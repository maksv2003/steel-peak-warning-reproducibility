# Dataset attribution and provenance

The file `data/Steel_industry_data.csv` is redistributed from **Steel Industry Energy Consumption**, created by **Sathishkumar V E, Changsun Shin and Yongyun Cho**, in the **UCI Machine Learning Repository**.

- Dataset page: [UCI dataset 851](https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption).
- Persistent identifier: [10.24432/C52G8C](https://doi.org/10.24432/C52G8C).
- Source archive: [UCI download](https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip).
- Original dataset license, as declared by UCI: [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- Attribution year: **2021**, following UCI's recommended citation. UCI separately displays a 2023 donation date.
- Provenance and checksum audit: **2026-10-20**.

UCI attributes the measurements to DAEWOO Steel Co. Ltd. in Gwangyang, South Korea. This repository does not claim ownership of the measurements or endorsement by the creators, UCI or the facility.

## File integrity and changes

SHA-256 of the bundled **CSV file** (not the ZIP):

```text
9b1cee6f9cb9cd9df2b95814ca90a9a2ff15b7f5f1fba0fae3c643e82072eacc
```

The CSV has 35,040 rows and 11 columns. The bundled source bytes are unmodified. The code verifies the checksum, preserves source row order and date strings, and computes derived features and predictions in memory. No interpolation, source timestamp correction, outlier deletion or hourly aggregation is applied.

The source dates are not strictly increasing: the audit finds **365 non-increasing timestamp steps** at the daily midnight positions. These remain in the CSV. Row offsets and the source's 96-record daily blocks define the experimental observation sequence.

Derived tables and figures in `results/` are products of this reconstruction and must not be represented as original UCI outputs.

The license statement above applies to the source dataset. It does not relicense the reconstruction code, cited papers, publisher content or other third-party materials.
