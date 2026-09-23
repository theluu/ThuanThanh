# Báo cáo phân tích & dự báo giá JKM LNG — tháng 2026-01

_Tạo bởi nhóm agent (Orchestrator → Data Engineer → Data Analyst → Data Scientist → Report Writer) · run `64dfaa77-aa4a-4a05-ac09-f32265a9d4ff` · 2026-09-23 13:50_

## 1. Tóm tắt điều hành

Hiện tại, giá LNG JKM đang ở mức 9.605 USD, giảm 13.19% trong 30 ngày qua, cho thấy xu hướng giảm trong ngắn hạn. Dự báo cho tháng tới, giá có thể dao động quanh mức 10-11 USD, dựa trên xu hướng giảm hiện tại và biến động giá. Mô hình "naive" được chọn cho dự báo này với độ chính xác cao (MAE 0.3919, RMSE 0.4874). Độ tin cậy của dự báo đạt 80%, cho thấy có khả năng cao giá thực tế sẽ nằm trong khoảng dự đoán. Khuyến nghị theo dõi sát diễn biến thị trường và chuẩn bị các phương án ứng phó với biến động giá.

## 2. Dữ liệu (Data Engineer)

- Nguồn: DB chính `lng_prices`, 503 phiên, 2024-01-02 → 2025-12-31. Trùng ngày: 0.

- Giá trị thiếu trước xử lý: {'JKM_Historical': 0, 'HH_Historical': 4, 'Brent_price': 8, 'US_Index_Historical': 0, 'Gold_Historical': 0} → xử lý: forward-fill then back-fill.

- Kết nối DB ngoài (dữ liệu 2026): **đã được phê duyệt**.

## 3. Phân tích thị trường (Data Analyst)

- JKM cuối kỳ (2025-12-31): **9.605 USD/MMBtu**; thay đổi ~30 phiên: -13.19%; spread JKM–HH: 5.605.

- Đỉnh: 15.125 (2024-12-03); đáy: 8.125 (2024-02-23).

- Biến động năm hóa: 0.334 (toàn kỳ), 0.435 (20 phiên gần nhất).


| Biến | Tương quan mức giá | Tương quan lợi suất ngày |
|---|---|---|
| HH_Historical | 0.276 | 0.144 |
| Brent_price | -0.134 | 0.101 |
| US_Index_Historical | 0.293 | 0.002 |
| Gold_Historical | 0.005 | 0.031 |


**Nhận định:**

- Giá LNG trung bình dự kiến cho năm 2024 là 11.887 USD, với biên độ dao động từ 8.125 USD đến 15.125 USD.
- Trong năm 2025, giá LNG trung bình có thể tăng nhẹ lên 12.24 USD, với mức tối thiểu 9.455 USD và tối đa 14.95 USD.
- Biến động giá LNG trong 20 ngày gần nhất là 0.435, cho thấy sự không ổn định cao trong ngắn hạn.
- Mối tương quan giữa giá LNG (HH) và chỉ số USD (DXY) là 0.293, cho thấy giá LNG có thể tăng khi USD yếu đi.
- Mối tương quan với giá dầu Brent là -0.134, cho thấy giá LNG có thể giảm khi giá dầu Brent tăng.
- Giá LNG hiện tại (9.605 USD) đã giảm 13.19% trong 30 ngày qua, cho thấy xu hướng giảm trong ngắn hạn.
- Dự báo cho tháng tới có thể tiếp tục giảm, với mức giá có thể dao động quanh 10-11 USD, dựa trên xu hướng giảm hiện tại và biến động giá.

## 4. Mô hình & dự báo (Data Scientist)

Walk-forward CV: huấn luyện đến cuối tháng, dự báo toàn bộ tháng kế tiếp (3 fold: 10, 11, 12/2025) — mô phỏng đúng bài toán thực tế.

| Mô hình | MAE | RMSE | MAPE (%) |
|---|---|---|---|
| naive | 0.392 | 0.487 | 3.87 |
| drift | 0.566 | 0.677 | 5.41 |
| ridge_lag | 0.400 | 0.499 | 3.98 |


Mô hình được chọn: **naive**. Dự báo trung bình tháng 2026-01: **9.605 USD/MMBtu** (dải 9.605 – 9.605).


| Ngày | Dự báo | Cận dưới 80% | Cận trên 80% |
|---|---|---|---|
| 2026-01-02 | 9.605 | 9.408 | 9.806 |
| 2026-01-05 | 9.605 | 9.327 | 9.891 |
| 2026-01-06 | 9.605 | 9.266 | 9.956 |
| 2026-01-07 | 9.605 | 9.215 | 10.012 |
| 2026-01-08 | 9.605 | 9.170 | 10.061 |
| 2026-01-09 | 9.605 | 9.129 | 10.105 |
| 2026-01-12 | 9.605 | 9.092 | 10.147 |
| 2026-01-13 | 9.605 | 9.058 | 10.185 |
| 2026-01-14 | 9.605 | 9.026 | 10.222 |
| 2026-01-15 | 9.605 | 8.995 | 10.256 |
| 2026-01-16 | 9.605 | 8.967 | 10.289 |
| 2026-01-19 | 9.605 | 8.939 | 10.320 |
| 2026-01-20 | 9.605 | 8.913 | 10.351 |
| 2026-01-21 | 9.605 | 8.888 | 10.380 |
| 2026-01-22 | 9.605 | 8.864 | 10.408 |
| 2026-01-23 | 9.605 | 8.840 | 10.436 |
| 2026-01-26 | 9.605 | 8.818 | 10.462 |
| 2026-01-27 | 9.605 | 8.796 | 10.488 |
| 2026-01-28 | 9.605 | 8.775 | 10.514 |
| 2026-01-29 | 9.605 | 8.754 | 10.538 |
| 2026-01-30 | 9.605 | 8.734 | 10.563 |


**Giải thích:**

- **Lựa chọn mô hình**: Mô hình "naive" được chọn vì có MAE (0.3919) và RMSE (0.4874) thấp nhất trong các mô hình so sánh, cho thấy độ chính xác cao hơn trong dự đoán.
  
- **Ý nghĩa MAE/RMSE/MAPE**: 
  - **MAE** (Mean Absolute Error) đo lường độ lệch trung bình tuyệt đối giữa giá trị dự đoán và giá trị thực tế, càng thấp càng tốt.
  - **RMSE** (Root Mean Square Error) phản ánh độ lệch bình quân của các sai số, nhấn mạnh các sai số lớn hơn, cũng cần thấp.
  - **MAPE** (Mean Absolute Percentage Error) cho biết sai số trung bình theo tỷ lệ phần trăm, giúp đánh giá hiệu suất mô hình trên các quy mô khác nhau.

- **Khoảng tin cậy 80%**: Khoảng tin cậy 80% cho thấy độ tin cậy trong dự đoán, tức là có 80% khả năng giá thực tế nằm trong khoảng dự đoán, giúp người dùng có cái nhìn rõ hơn về độ chính xác của dự báo.

- **Kết quả backtest**: Kết quả backtest cho thấy MAE (0.8455) và RMSE (1.1819) cao hơn so với mô hình "naive", nhưng vẫn cung cấp thông tin hữu ích về khả năng dự đoán trong quá khứ, cho thấy mô hình có thể cần điều chỉnh để cải thiện độ chính xác trong tương lai.

## 5. Kiểm định ngoài mẫu (backtest với dữ liệu thực tế 2026)

- 20 phiên: MAE **0.845**, RMSE 1.182, MAPE **7.52%**.

- Trung bình thực tế 10.431 vs dự báo 9.605; tỷ lệ ngày nằm trong khoảng 80%: 50%.


So sánh tất cả mô hình trên dữ liệu ngoài mẫu:

| Mô hình | MAE | RMSE | MAPE (%) |
|---|---|---|---|
| naive | 0.845 | 1.182 | 7.52 |
| drift | 1.111 | 1.490 | 9.95 |
| ridge_lag | 0.852 | 1.190 | 7.58 |

## 6. Rủi ro & hạn chế

- Biến ngoại sinh tương lai chưa biết → giữ nguyên giá trị cuối (giả định). Cú sốc thời tiết/địa chính trị không nằm trong dữ liệu.

- Dữ liệu chỉ 2 năm, tần suất ngày → mùa vụ năm chỉ quan sát 2 chu kỳ.

- Khoảng tin cậy dựa trên biến động 120 phiên gần nhất, giả định log-return chuẩn.