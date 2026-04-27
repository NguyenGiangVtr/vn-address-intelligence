import asyncio
from playwright.async_api import async_playwright
import logging
from app.core.database import SessionLocal
from sqlalchemy import text as sql_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GSOPlywright")

class GSOPlywrightCrawler:
    def __init__(self):
        self.url = "https://danhmuchanhchinh.nso.gov.vn/Default.aspx"
        self.batch_data = []

    async def run(self, start_page=1, end_page=5):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await context.new_page()
            
            logger.info(f"Navigating to {self.url}...")
            await page.goto(self.url, wait_until="networkidle")
            
            # Đợi trang ổn định
            await asyncio.sleep(2)

            # 1. Chọn cấp 'Xã' - Dùng Text selector
            logger.info("Selecting level 'Xã'...")
            try:
                # Click vào dropdown 'Cấp'
                await page.click("xpath=//table[contains(@id, 'cmbCap')]//td[contains(@class, 'dxic')]")
                await asyncio.sleep(1.5)
                # Chọn 'Xã'
                await page.click("xpath=//td[contains(@class, 'dxeListBoxItem') and text()='Xã']")
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Level selection failed: {e}. Trying direct selection...")
            
            # 2. Nhấn 'Thực Hiện' - Dùng Text selector
            logger.info("Clicking 'Thực Hiện'...")
            try:
                await page.click("xpath=//span[text()='Thực Hiện']/parent::*")
                await asyncio.sleep(5) # Chờ AJAX bắt đầu
                await page.wait_for_load_state("networkidle", timeout=60000)
            except Exception as e:
                logger.error(f"Click 'Thực Hiện' failed: {e}")
                await page.screenshot(path="error_thuchien.png")

            current_page = 1
            # Chuyển trang nếu cần
            while current_page < start_page:
                next_pg = page.locator(f"xpath=//td[contains(@class, 'dxpPageNumber') and text()='{current_page + 1}']")
                if await next_pg.count() > 0:
                    await next_pg.click()
                    await asyncio.sleep(3)
                    current_page += 1
                else: break

            while current_page <= end_page:
                logger.info(f"--- Processing Page {current_page} ---")
                await page.wait_for_selector("tr.dxgvDataRow", timeout=30000)
                rows = await page.query_selector_all("tr.dxgvDataRow")
                
                for i in range(len(rows)):
                    try:
                        # Refetch rows
                        rows = await page.query_selector_all("tr.dxgvDataRow")
                        row = rows[i]
                        cells = await row.query_selector_all("td")
                        
                        code = (await cells[1].inner_text()).strip()
                        name = (await cells[2].inner_text()).strip()
                        level = (await cells[4].inner_text()).strip()
                        
                        # Click để mở chi tiết
                        await cells[2].click()
                        await asyncio.sleep(3) # Chờ chi tiết load
                        
                        # Lấy Dân số, Diện tích
                        pop_el = page.locator("xpath=//input[contains(@id, 'txtDANSO_I')]").last
                        area_el = page.locator("xpath=//input[contains(@id, 'txtDIENTICH_I')]").last
                        
                        pop_val = await pop_el.input_value() if await pop_el.count() > 0 else "0"
                        area_val = await area_el.input_value() if await area_el.count() > 0 else "0"
                        
                        logger.info(f"✅ [{current_page}.{i+1}] {name} ({code}): {pop_val} người, {area_val} km2")
                        
                        self.batch_data.append({
                            'code': code, 'level': level,
                            'population': self._clean_num(pop_val),
                            'area_km2': self._clean_num(area_val),
                            'notes': f"GSO 2025 Crawler - Page {current_page}"
                        })
                        
                        # Đóng chi tiết
                        cancel_btn = page.locator("xpath=//input[contains(@id, 'btnCancel')]").last
                        if await cancel_btn.count() > 0:
                            await cancel_btn.click()
                            await asyncio.sleep(0.5)
                        else:
                            await page.keyboard.press("Escape")
                        
                        if len(self.batch_data) >= 10:
                            self._save_to_db()
                            self.batch_data = []

                    except Exception as e:
                        logger.warning(f"Row {i} error: {e}")
                        await page.keyboard.press("Escape")
                        continue
                
                self._save_to_db()
                self.batch_data = []
                
                # Next Page
                current_page += 1
                next_pg = page.locator(f"xpath=//td[contains(@class, 'dxpPageNumber') and text()='{current_page}']")
                if await next_pg.count() > 0:
                    await next_pg.click()
                    await asyncio.sleep(4)
                else: break
            
            await browser.close()

    def _clean_num(self, val):
        if not val: return 0
        try: return float(val.replace('.', '').replace(',', '.'))
        except: return 0

    def _save_to_db(self):
        if not self.batch_data: return
        session = SessionLocal()
        try:
            for item in self.batch_data:
                code = item['code']
                if len(code) <= 2: table, id_col = "mat.province", "province_no"
                elif len(code) <= 3: table, id_col = "mat.district", "district_no"
                else: table, id_col = "mat.ward", "ward_no"
                
                session.execute(sql_text(f"""
                    UPDATE {table} SET admin_version = 2, population = :p, area_km2 = :a, notes = :n
                    WHERE {id_col} = :c OR {id_col} = :cz
                """), {'p': item['population'], 'a': item['area_km2'], 'n': item['notes'], 'c': code, 'cz': code.zfill(2 if table == "mat.province" else 3 if table == "mat.district" else 5)})
            session.commit()
            logger.info(f"Saved {len(self.batch_data)} rows.")
        except Exception as e:
            session.rollback()
            logger.error(f"DB Error: {e}")
        finally: session.close()
