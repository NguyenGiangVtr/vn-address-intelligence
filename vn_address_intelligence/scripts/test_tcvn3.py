import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from io import StringIO

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

# TCVN3 (ABC) byte -> Unicode character map
# Based on TCVN 5712:1993 standard
TCVN3 = {
    0x80: '\u00c0', 0x81: '\u1ea2', 0x82: '\u00c3', 0x83: '\u00c1',
    0x84: '\u1ea0', 0x85: '\u1eb6', 0x86: '\u1ea6', 0x87: '\u1ea8',
    0x88: '\u1eaa', 0x89: '\u1eac', 0x8a: '\u1ea4', 0x8b: '\u00c3',
    0x8c: '\u1eb0', 0x8d: '\u1eb2', 0x8e: '\u1eb4', 0x8f: '\u1eb4',
    0x90: '\u00ca', 0x91: '\u1eba', 0x92: '\u1ebb', 0x93: '\u1ebd',
    0x94: '\u00c9', 0x95: '\u1eb8', 0x96: '\u1ec0', 0x97: '\u1ec2',
    0x98: '\u1ec4', 0x99: '\u1ec6', 0x9a: '\u1ebe', 0x9b: '\u00cd',
    0x9c: '\u1ec8', 0x9d: '\u0128', 0x9e: '\u1eca', 0x9f: '\u0110',
    0xa0: '\u0111', 0xa1: '\u00d2', 0xa2: '\u1ece', 0xa3: '\u00d5',
    0xa4: '\u00d3', 0xa5: '\u1ecc', 0xa6: '\u1ed8', 0xa7: '\u1eda',
    0xa8: '\u1edc', 0xa9: '\u1ede', 0xaa: '\u1ee0', 0xab: '\u1ed2',
    0xac: '\u1ed4', 0xad: '\u1ed6', 0xae: '\u01a0', 0xaf: '\u1ed0',
    0xb0: '\u1ee2', 0xb1: '\u00da', 0xb2: '\u1ee6', 0xb3: '\u0168',
    0xb4: '\u00da', 0xb5: '\u1ee4', 0xb6: '\u1ef0', 0xb7: '\u1ee8',
    0xb8: '\u1eea', 0xb9: '\u1eec', 0xba: '\u1eee', 0xbb: '\u01af',
    0xbc: '\u1ef2', 0xbd: '\u1ef6', 0xbe: '\u1ef8', 0xbf: '\u00dd',
    0xc0: '\u1ef4', 0xc1: '\u00e0', 0xc2: '\u1ea3', 0xc3: '\u00e3',
    0xc4: '\u00e1', 0xc5: '\u1ea1', 0xc6: '\u1eb7', 0xc7: '\u1ea7',
    0xc8: '\u1ea9', 0xc9: '\u1eab', 0xca: '\u1ead', 0xcb: '\u1ea5',
    0xcc: '\u0103', 0xcd: '\u1eb1', 0xce: '\u1eb3', 0xcf: '\u1eb5',
    0xd0: '\u1eb5', 0xd1: '\u00ea', 0xd2: '\u1ebb', 0xd3: '\u1ebc',
    0xd4: '\u1ebd', 0xd5: '\u00e9', 0xd6: '\u1eb9', 0xd7: '\u1ec1',
    0xd8: '\u1ec3', 0xd9: '\u1ec5', 0xda: '\u1ec7', 0xdb: '\u1ebf',
    0xdc: '\u00ed', 0xdd: '\u1ec9', 0xde: '\u0129', 0xdf: '\u1ecb',
    0xe0: '\u00f2', 0xe1: '\u1ecf', 0xe2: '\u00f5', 0xe3: '\u00f3',
    0xe4: '\u1ecd', 0xe5: '\u1ed9', 0xe6: '\u1edb', 0xe7: '\u1edd',
    0xe8: '\u1edf', 0xe9: '\u1ee1', 0xea: '\u1ed3', 0xeb: '\u1ed5',
    0xec: '\u1ed7', 0xed: '\u01a1', 0xee: '\u1ed1', 0xef: '\u1ee3',
    0xf0: '\u00fa', 0xf1: '\u1ee7', 0xf2: '\u0169', 0xf3: '\u00fa',
    0xf4: '\u1ee5', 0xf5: '\u1ef1', 0xf6: '\u1ee9', 0xf7: '\u1eeb',
    0xf8: '\u1eed', 0xf9: '\u1eef', 0xfa: '\u01b0', 0xfb: '\u00fd',
    0xfc: '\u1ef3', 0xfd: '\u1ef7', 0xfe: '\u1ef9', 0xff: '\u1ef5',
}

def decode_tcvn3_bytes(raw):
    chars = []
    for b in raw:
        if b < 0x80:
            chars.append(chr(b))
        elif b in TCVN3:
            chars.append(TCVN3[b])
        else:
            chars.append('?')
    return ''.join(chars)

# Test province file
fp = os.path.join(base, 'nso-gov-province_25_04_2026.csv')
with open(fp, 'rb') as f:
    raw = f.read()

decoded = decode_tcvn3_bytes(raw)
print("=== Province file decoded (first 400 chars) ===")
print(decoded[:400])

# Parse
try:
    df = pd.read_csv(StringIO(decoded), on_bad_lines='skip')
    print(f"\nShape: {df.shape}, Cols: {list(df.columns)}")
    print("Sample data:")
    for _, row in df.head(4).iterrows():
        print(f"  {list(row.values)}")
except Exception as e:
    print(f"Parse error: {e}")
    # Try tab
    lines = decoded.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    for l in lines[:5]:
        print(f"  LINE: {l[:150]}")

# Test ward file
print("\n=== Ward file decoded (first 500 chars) ===")
fp2 = os.path.join(base, 'nso-gov-ward_25_04_2026.csv')
with open(fp2, 'rb') as f:
    raw2 = f.read()
decoded2 = decode_tcvn3_bytes(raw2)
print(decoded2[:500])
