import re

class PreLabeler:
    @staticmethod
    def predict(text: str) -> list:
        results = []
        # Improved NUM regex
        num_match = re.search(r'^(Số\s+[\d\w/.\-]+|(?=\d)[\d\w/.\-]+)', text, re.I)
        if num_match:
            matched_text = num_match.group(0)
            if any(char.isdigit() for char in matched_text) or matched_text.lower().startswith("số "):
                results.append({
                    "from_name": "label", "to_name": "text", "type": "labels",
                    "score": 0.9,
                    "value": {
                        "start": num_match.start(0),
                        "end": num_match.end(0),
                        "text": matched_text,
                        "labels": ["NUM"]
                    }
                })
        return results

test_text = "Cẩm Giang Tạp Hóa"
print(f"Testing: '{test_text}'")
print(f"Result: {PreLabeler.predict(test_text)}")

test_text_2 = "123/45 Lê Lợi"
print(f"Testing: '{test_text_2}'")
print(f"Result: {PreLabeler.predict(test_text_2)}")

test_text_3 = "Số 15A Trần Hưng Đạo"
print(f"Testing: '{test_text_3}'")
print(f"Result: {PreLabeler.predict(test_text_3)}")
