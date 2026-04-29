import pandas as pd, re

fpath = r'd:\2.GIT SOURCE\vn-address-intelligence\data\seed\AdministrativeUnitConversion.csv'
df = pd.read_csv(fpath, encoding='cp850', dtype=str)
df.columns = ['province_new','ward_name_new','ward_code_new','ward_name_old','ward_code_old','note','district_old','province_old','x1','x2']
df = df[df['ward_name_new'].notna()].copy()

def code(s):
    if pd.isna(s): return None
    m = re.search(r'\(0*(\d+)\)', str(s))
    return int(m.group(1)) if m else None

def name_clean(s):
    if pd.isna(s): return None
    return re.sub(r'\s*\([\d]+\)\s*$', '', str(s).strip())

df['prov_code_new'] = df['province_new'].apply(code)
df['prov_code_old'] = df['province_old'].apply(code)
df['dist_code_old'] = df['district_old'].apply(code)
df['prov_name_new'] = df['province_new'].apply(name_clean)
df['prov_name_old'] = df['province_old'].apply(name_clean)
df['dist_name_old'] = df['district_old'].apply(name_clean)
df['note_clean'] = df['note'].str.strip().str.replace(r'\s+', ' ', regex=True)

def classify(note):
    if pd.isna(note): return 'UNKNOWN'
    n = str(note).strip().lower()
    if 'gi?' in n[:8]: return 'RETAINED'
    if '?i tên' in n: return 'RENAMED'
    if '?i lo?i hình' in n: return 'TYPE_CHANGED'
    if 'toàn b?' in n and 's?p x?p' not in n: return 'MERGED_FULL'
    if 'di?n tích' in n and 'dân s?' in n: return 'MERGED_PARTIAL'
    if 'di?n tích' in n: return 'MERGED_AREA'
    if 'dân s?' in n: return 'MERGED_POPULATION'
    if 'm?t ph?n' in n or 'ph?n còn l?i' in n: return 'MERGED_PARTIAL'
    if 's?p x?p' in n: return 'SPECIAL_ZONE'
    return 'OTHER'

df['rel_type'] = df['note_clean'].apply(classify)

print('=== relationship_type distribution:')
print(df['rel_type'].value_counts())
print()

print('=== Ward mapping summary:')
print('Total mapping rows       :', len(df))
print('Unique new wards (v2)    :', df['ward_code_new'].nunique())
print('Unique old wards (v1)    :', df['ward_code_old'].dropna().nunique())
cross_prov = df[df['prov_code_new'] != df['prov_code_old']]
print('Cross-province merges    :', len(cross_prov))
print('New provinces (v2)       :', df['prov_code_new'].nunique())
print('Old provinces absorbed   :', df['prov_code_old'].nunique())
print()

merge_counts = df.groupby('ward_code_new')['ward_code_old'].count()
print('=== Old wards per new ward (top):')
print(merge_counts.value_counts().sort_index().head(15))
print('Max merge-in:', merge_counts.max(), '-> ward_code_new =', merge_counts.idxmax())
print()

special = df[df['rel_type'] == 'SPECIAL_ZONE']
print('=== Special Zone conversions:')
print(special[['prov_name_new','ward_name_new','ward_code_new','ward_name_old','note_clean']].to_string())
print()

print('=== Province-level merge: wards going cross-province (sample 15):')
print(cross_prov[['prov_name_old','prov_code_old','prov_name_new','prov_code_new','ward_name_old','ward_name_new']].drop_duplicates('prov_code_old').head(30).to_string())
print()

print('=== Provinces absorbed (v1 codes NOT in v2):')
old_set = set(df['prov_code_old'].dropna().astype(int))
new_set = set(df['prov_code_new'].dropna().astype(int))
absorbed = old_set - new_set
print('Absorbed (removed) province codes:', sorted(absorbed))
print('New province codes:', sorted(new_set))
print()

print('=== Sample note=RETAINED (ward_code same):')
retained = df[df['rel_type'] == 'RETAINED']
same_code = retained[retained['ward_code_new'] == retained['ward_code_old']]
diff_code = retained[retained['ward_code_new'] != retained['ward_code_old']]
print('  Same code (pure retain):', len(same_code))
print('  Different code (province-move + retain):', len(diff_code))
print(diff_code[['prov_name_old','prov_name_new','ward_name_old','ward_name_new','ward_code_old','ward_code_new']].head(10).to_string())
