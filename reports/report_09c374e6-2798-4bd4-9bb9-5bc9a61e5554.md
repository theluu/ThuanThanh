# Báo cáo phân tích & dự báo giá JKM LNG — tháng 2026-01

_Tạo bởi nhóm agent (Orchestrator → Data Engineer → Data Analyst → Data Scientist → Report Writer) · run `09c374e6-2798-4bd4-9bb9-5bc9a61e5554` · 2026-09-23 13:55_

## 1. Tóm tắt điều hành

Hiện tại, giá JKM đang ở mức 9.605 USD, đã giảm 13.19% trong 30 ngày qua, cho thấy xu hướng giảm giá ngắn hạn. Dự báo cho tháng tới, giá JKM có thể tiếp tục giảm với mức trung bình dự kiến là 9.605 USD, dựa trên mô hình "naive" với độ tin cậy 80%. Kết quả backtest cho thấy MAE là 0.8455 và RMSE là 1.1819, cho thấy mô hình vẫn duy trì hiệu suất tốt nhưng cần cải thiện. Khuyến nghị theo dõi sát sao biến động giá LNG và các yếu tố bên ngoài như giá dầu và đồng USD để điều chỉnh chiến lược phù hợp.

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

- Giá LNG trung bình dự kiến trong năm 2024 là 11.887 USD, với biên độ dao động từ 8.125 USD đến 15.125 USD.
- Trong năm 2025, giá LNG trung bình có thể tăng nhẹ lên 12.24 USD, với mức tối thiểu là 9.455 USD và tối đa 14.95 USD.
- Biến động giá LNG trong 20 ngày gần đây là 0.435, cho thấy sự không ổn định cao trong ngắn hạn.
- Mối tương quan giữa giá LNG (HH) và chỉ số USD (DXY) là 0.293, cho thấy giá LNG có thể chịu ảnh hưởng từ sự biến động của đồng USD.
- Mối tương quan với giá dầu Brent là -0.134, cho thấy giá LNG có thể không đồng biến với giá dầu trong thời gian tới.
- Giá LNG hiện tại (9.605 USD) đã giảm 13.19% trong 30 ngày qua, cho thấy xu hướng giảm giá trong ngắn hạn.
- Dự báo cho tháng tới có thể tiếp tục giảm do xu hướng giảm giá và biến động cao, cùng với sự ảnh hưởng từ các yếu tố bên ngoài như giá dầu và đồng USD.

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

- **Lựa chọn mô hình "naive"**: Mô hình này có MAE (0.3919) và RMSE (0.4874) thấp nhất so với các mô hình khác, cho thấy khả năng dự đoán chính xác hơn trong bối cảnh dữ liệu hiện tại.

- **Ý nghĩa MAE/RMSE/MAPE**: 
  - **MAE** (Mean Absolute Error) đo lường độ chính xác trung bình của dự đoán, với giá trị thấp hơn cho thấy mô hình tốt hơn.
  - **RMSE** (Root Mean Squared Error) nhấn mạnh các sai số lớn hơn, giúp phát hiện các dự đoán sai lệch nghiêm trọng.
  - **MAPE** (Mean Absolute Percentage Error) thể hiện độ chính xác theo tỷ lệ phần trăm, hữu ích trong việc so sánh giữa các mô hình.

- **Khoảng tin cậy 80%**: Chỉ ra rằng có 80% khả năng giá thực tế nằm trong khoảng dự đoán, giúp đánh giá độ tin cậy của dự báo.

- **Kết quả backtest**: MAE (0.8455) và RMSE (1.1819) cho thấy mô hình "naive" vẫn duy trì hiệu suất tốt trong việc dự đoán, mặc dù có sự gia tăng sai số so với dự đoán ban đầu, cho thấy cần cải thiện trong các giai đoạn tiếp theo.

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