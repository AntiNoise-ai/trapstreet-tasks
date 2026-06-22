# Image License & Attribution

The 20 receipt images in `inputs/*/document.jpg` are derived from **CORD-v2** (Consolidated Receipt Dataset).

## Source

**CORD: A Consolidated Receipt Dataset for Post-OCR Parsing**
Park, Seunghyun et al. (2019). Document Intelligence Workshop at NeurIPS 2019.
HuggingFace dataset: https://huggingface.co/datasets/naver-clova-ix/cord-v2
Maintained by Naver CLOVA.

## License

The original CORD-v2 dataset is released under **Creative Commons Attribution 4.0 International (CC BY 4.0)**:
https://creativecommons.org/licenses/by/4.0/

Attribution required. Redistribution allowed.

## What was modified

- **Sampled 25 receipts** from the CORD-v2 `train` split (1,000 receipts total). Used 20 across the 4 question types (some receipts appear in multiple question categories — each `case_id` is unique but the underlying image may be shared).
- **No image content changed.** Re-saved as JPEG quality 85 (same compression as source).
- **Pre-filtered out** receipts whose total used Indonesian period-as-thousand-separator notation (e.g. `48.000` meaning 48,000) — those numeric formats are ambiguous and would inflate judge false-negatives. Comma notation only.
- **Ground truth** was extracted from each receipt's `gt_parse.total.total_price`, `menu` length, `gt_parse.sub_total.subtotal_price`, and `gt_parse.sub_total.tax_price` fields.

## Receipt content

Receipts are from real restaurants/shops, primarily in Indonesia and other Southeast Asian markets. Merchant names and other PII are blurred in the source images by Naver CLOVA. Text on receipts is mixed Indonesian + English. All currency is Indonesian Rupiah (IDR).

## Citation

```bibtex
@article{park2019cord,
  author = {Park, Seunghyun and Shin, Seunghyun and Lee, Bado and Lee, Junyeop and Surh, Jaeheung and Seo, Minjoon and Lee, Hwalsuk},
  title = {CORD: A Consolidated Receipt Dataset for Post-OCR Parsing},
  journal = {Document Intelligence Workshop at NeurIPS},
  year = {2019}
}
```
