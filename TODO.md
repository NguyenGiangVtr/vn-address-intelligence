# TODO: Cập nhật Training cho Label Studio Import

## ✅ Plan đã được approve
- [ ] **app/ai/train_ner.py**: Thêm mapping text→value labels trong `convert_labelstudio_to_bio`
- [ ] **app/main.py**: Thêm CLI `import-labelstudio` để convert standalone
- [ ] Test với sample LS JSON
- [ ] Update UI nếu cần

**Current step:** Đang implement app/ai/train_ner.py
