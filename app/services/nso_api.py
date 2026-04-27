import requests
import xml.etree.ElementTree as ET
from datetime import datetime

NSO_URL = "https://danhmuchanhchinh.nso.gov.vn/DMDVHC.asmx"

def call_nso_soap(action, body_content):
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    {body_content}
  </soap:Body>
</soap:Envelope>"""
    
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f"http://tempuri.org/{action}"
    }
    
    try:
        # Disable SSL verification for NSO as it often has cert issues
        response = requests.post(NSO_URL, data=soap_body.encode('utf-8'), headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        raise Exception(f"NSO SOAP Error ({action}): {str(e)}")

def parse_nso_xml(xml_content, action):
    try:
        # Find the start of the diffgram to simplify parsing if needed, 
        # or parse normally but handle the nested structure.
        root = ET.fromstring(xml_content)
        
        # Namespaces
        ns = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/',
            'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
            'msdata': 'urn:schemas-microsoft-com:xml-msdata'
        }
        
        # The structure is: soap:Envelope -> soap:Body -> ActionResponse -> ActionResult -> diffgr:diffgram -> DocumentElement -> TABLE
        result_tag = f".//ns:{action}Result"
        result_node = root.find(result_tag, ns)
        
        if result_node is None:
            return []

        diffgram = result_node.find("diffgr:diffgram", ns)
        if diffgram is None:
            # Fallback for empty results
            return []
            
        # Inside diffgram, there is a DocumentElement (sometimes no namespace)
        document_element = diffgram.find("DocumentElement")
        if document_element is None:
            # Try with namespace if any, though usually it's empty xmlns=""
            document_element = diffgram.find("{ }DocumentElement")
            
        if document_element is None:
            # Final attempt: just find any TABLE inside diffgram
            tables = diffgram.findall(".//TABLE")
        else:
            tables = document_element.findall("TABLE")
            
        items = []
        for table in tables:
            item = {}
            for child in table:
                # child.tag might have namespace prefix if not careful
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                item[tag] = child.text
            items.append(item)
        return items
    except Exception as e:
        print(f"XML Parsing Error: {e}")
        return []

def get_nso_provinces(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime('%d/%m/%Y')
    
    body = f"""<DanhMucTinh xmlns="http://tempuri.org/">
      <DenNgay>{date_str}</DenNgay>
    </DanhMucTinh>"""
    
    xml_res = call_nso_soap("DanhMucTinh", body)
    return parse_nso_xml(xml_res, "DanhMucTinh")

def get_nso_districts(province_no="", province_name="", date_str=None):
    if not date_str:
        date_str = datetime.now().strftime('%d/%m/%Y')
        
    body = f"""<DanhMucQuanHuyen xmlns="http://tempuri.org/">
      <DenNgay>{date_str}</DenNgay>
      <Tinh>{province_no}</Tinh>
      <TenTinh>{province_name}</TenTinh>
    </DanhMucQuanHuyen>"""
    
    xml_res = call_nso_soap("DanhMucQuanHuyen", body)
    return parse_nso_xml(xml_res, "DanhMucQuanHuyen")

def get_nso_wards(province_no="", province_name="", district_no="", district_name="", date_str=None):
    if not date_str:
        date_str = datetime.now().strftime('%d/%m/%Y')
        
    body = f"""<DanhMucPhuongXa xmlns="http://tempuri.org/">
      <DenNgay>{date_str}</DenNgay>
      <Tinh>{province_no}</Tinh>
      <TenTinh>{province_name}</TenTinh>
      <QuanHuyen>{district_no}</QuanHuyen>
      <TenQuanHuyen>{district_name}</TenQuanHuyen>
    </DanhMucPhuongXa>"""
    
    xml_res = call_nso_soap("DanhMucPhuongXa", body)
    return parse_nso_xml(xml_res, "DanhMucPhuongXa")
