# Source verification and citation scope

Checked **2026-10-20** against publisher, repository and author records. These are the manuscript's ten references, not a claim that each cited paper independently validates this reconstruction. Full citation metadata, additional evidence links and limitations are in [references_audit.json](references_audit.json).

All ten sources were identified. No invalid DOI or nonexistent publication was established. Some direct requests returned 403/429 or a tool fetch error while indexed text from the publisher remained available. These are access limitations, not evidence that the identifier is wrong. Subscription access, anti-bot restrictions and link validity are separate questions.

## 1. UCI source dataset

Sathishkumar V E, C. Shin and Y. Cho. *Steel Industry Energy Consumption*. UCI Machine Learning Repository, 2021. DOI: [10.24432/C52G8C](https://doi.org/10.24432/C52G8C).

- Canonical page: [UCI dataset 851](https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption).
- Access: official page readable; download link available. The DOI route itself could not be fetched by the checking tool.
- Verified: creators, title, DOI and recommended citation year. The separate donation date shown by UCI is 2023-08-13; the recommended citation uses 2021.
- Supports: facility provenance, 35,040 records, variable descriptions, kWh units and the repository's missing-value statement. It does not establish any model result. Dataset rights and the exact CSV checksum are recorded in [DATA_LICENSE.md](DATA_LICENSE.md).

## 2. Original dataset-related prediction study

V. E. Sathishkumar, C. Shin and Y. Cho. “Efficient energy consumption prediction model for a data analytic-enabled industry building in a smart city.” *Building Research & Information*, 49(1), 127–143, 2021. DOI: [10.1080/09613218.2020.1809983](https://doi.org/10.1080/09613218.2020.1809983).

- Canonical page: [Taylor & Francis](https://www.tandfonline.com/doi/abs/10.1080/09613218.2020.1809983).
- Access: direct request returned 403; publisher-domain indexed metadata and abstract were available. Full-text access was not established.
- Verified: authors, title, issue, pages and DOI. Online publication was in September 2020, whereas volume 49(1) is dated 2021.
- Supports: comparison of data-mining predictors on a South Korean steel facility. UCI identifies this as its introductory paper. This is background support, not validation of the current chronological warning experiment.

## 3. CatBoost for steel-energy prediction

K. Karthick, R. Dharmaprakash and S. Sathya. “Predictive modeling of energy consumption in the steel industry using CatBoost regression: A data-driven approach for sustainable energy management.” *International Journal of Robotics and Control Systems*, 4(1), 33–49, 2024. DOI: [10.31763/ijrcs.v4i1.1234](https://doi.org/10.31763/ijrcs.v4i1.1234).

- Canonical page: [ASCEE article 1234](https://pubs2.ascee.org/index.php/IJRCS/article/view/1234).
- Access: direct article/issue requests returned 403. Indexed publisher metadata, the [issue contents](https://pubs2.ascee.org/index.php/IJRCS/issue/view/78), and the [PDF first page](https://www.pubs2.ascee.org/index.php/IJRCS/article/download/1234/pdf) confirmed the citation. The publisher declares an open license.
- Verified: all citation fields, including the real DOI suffix `1234`.
- Supports: use of CatBoost regression on steel-energy data. Its abstract describes 5-fold GridSearchCV; the citation does not show that its evaluation and the warning-budget protocol are identical.

## 4. Multi-sequence steel-load forecasting

Z. Wang, M. Ding, Z. Cai, W. Yu and X. Luo. “Short term steel plant load forecasting based on multi sequence LSTM recurrent neural network and self-organizing neural network.” *The Journal of Engineering*, 2025(1), **e70100**, 2025. DOI: [10.1049/tje2.70100](https://doi.org/10.1049/tje2.70100).

- Canonical page: [Wiley / IET](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/tje2.70100).
- Access: full publisher text readable, marked Open Access.
- Verified: authors, title, year, volume/issue, DOI and article number. The manuscript's original reference omitted `e70100`.
- Supports: multi-sequence LSTM forecasting in steel plants. The paper describes ten Chinese plants and 2015 data, rather than the present UCI case.

## 5. Prediction with attention to peak periods

L. Yi, D. Yu, Y. Wang, B. Luo and X. Peng. “Ultra-short-term forecasting study of power load in mega steel industry based on multi-stage modeling.” *Recent Patents on Mechanical Engineering*, 19(1), 131–149, 2026. DOI: [10.2174/0122127976360100241221192728](https://doi.org/10.2174/0122127976360100241221192728).

- Canonical page: [Bentham Science](https://www.benthamscience.com/public/article/145936).
- Access: citation and abstract readable; PDF is behind purchase/login controls.
- Verified: all citation fields. The issue is dated **2026**, although the online publication date is 20 January 2025.
- Supports: ultra-short-term load prediction with peak-period accuracy as an objective. The available abstract describes an LSTM-XGBoost-based method; its complete methods were not audited.

## 6. Forecasting in energy-intensive manufacturing

A. M. N. C. Ribeiro, P. R. X. do Carmo, I. R. Rodrigues, D. Sadok, T. Lynn and P. T. Endo. “Short-term firm-level energy-consumption forecasting for energy-intensive manufacturing: A comparison of machine learning and deep learning models.” *Algorithms*, 13(11), 274, 2020. DOI: [10.3390/a13110274](https://doi.org/10.3390/a13110274).

- Canonical page: [MDPI](https://www.mdpi.com/1999-4893/13/11/274).
- Access: direct request returned 429 or a fetch error; indexed publisher text and [citation/version notes](https://www.mdpi.com/1999-4893/13/11/274/notes) were available. The article is marked Open Access.
- Verified: authors, title, year, volume/issue, article number and DOI.
- Supports: comparing ML/DL approaches for industrial energy forecasting. Its case is a Brazilian thermoplastic resin plant, so it should not be described as a steel-plant experiment.

## 7. Out-of-sample forecasting evaluation

L. J. Tashman. “Out-of-sample tests of forecasting accuracy: an analysis and review.” *International Journal of Forecasting*, 16(4), 437–450, 2000. DOI: [10.1016/S0169-2070(00)00065-0](https://doi.org/10.1016/S0169-2070(00)00065-0).

- Canonical page: [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0169207000000650).
- Access: DOI request returned 403 and direct publisher retrieval failed; indexed publisher citation, abstract and section snippets were available. Full text was not read.
- Verified: all citation fields.
- Supports: separating fitting from later evaluation, forecasting origins and rolling evaluation. It also discusses multiple test periods. It does not guarantee that this experiment's calibrated false-warning allowance transfers to later data.

## 8. Original CatBoost method

L. Prokhorenkova, G. Gusev, A. Vorobev, A. V. Dorogush and A. Gulin. “CatBoost: unbiased boosting with categorical features.” *Advances in Neural Information Processing Systems*, 31, 6638–6648, 2018.

- Canonical page: [NeurIPS proceedings](https://papers.nips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html).
- Access: official abstract and [JSON metadata](https://papers.nips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Metadata.json) readable; paper and supplementary links available.
- Verified: authors, title, year, volume and page range. The page range completes the manuscript reference. No DOI is supplied here.
- Supports: CatBoost's method identity and its underlying boosting techniques. Hyperparameters used in this repository are reconstruction settings, not values justified by this citation alone.

## 9. Precision–recall evaluation under imbalance

T. Saito and M. Rehmsmeier. “The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets.” *PLOS ONE*, 10(3), e0118432, 2015. DOI: [10.1371/journal.pone.0118432](https://doi.org/10.1371/journal.pone.0118432).

- Canonical page: [PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).
- Access: full text readable. The DOI redirected to PLOS but one redirect route failed in the checking tool; the canonical article route worked.
- Verified: all citation fields.
- Supports: precision–recall analysis for imbalanced labels. The full-text search did not find “average precision.” Accordingly, this reference motivates PR evaluation but is not the definition of the particular AP estimator used here. The executable code uses `sklearn.metrics.average_precision_score`.

## 10. Bootstrap for dependent observations

H. R. **Künsch**. “The jackknife and the bootstrap for general stationary observations.” *The Annals of Statistics*, 17(3), 1217–1241, 1989. DOI: [10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265).

- Canonical page: [Project Euclid](https://projecteuclid.org/journals/annals-of-statistics/volume-17/issue-3/The-Jackknife-and-the-Bootstrap-for-General-Stationary-Observations/10.1214/aos/1176347265.full).
- Access: the DOI resolved to the correct title/volume/issue page, but the article and PDF routes returned an iframe shell to the tool. The [author's ETH bibliography](https://people.math.ethz.ch/~kuensch/papers/) independently confirms title, year, volume and pages.
- Verified: consistent citation metadata; the author's spelling uses the umlaut in Künsch.
- Supports: the foundation of block resampling for dependent stationary observations. This does not itself establish seven days as an optimal block length or validate intervals under distribution change. The reconstruction's circular sampling rule is explicitly specified in [METHODOLOGY.md](METHODOLOGY.md). [Official boodd documentation](https://www.stat.math.ethz.ch/CRAN/web/packages/boodd/refman/boodd.html) distinguishes Künsch's moving-block approach from the circular approach attributed to Politis and Romano (1992); that additional original chapter was not part of the ten-source audit.

## Rights and interpretation

This file provides bibliographic metadata and short verification notes. It does not redistribute the cited papers or grant rights in them. Publication existence, a correct DOI and topical relevance do not establish that this reconstruction reproduces every original numerical result. See [README.md](README.md) for the observed agreements and discrepancies.
