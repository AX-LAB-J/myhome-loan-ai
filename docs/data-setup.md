# 데이터와 모델 준비

이 저장소는 교육용 가상 금융 데이터로 동작합니다. CSV·DB·학습 모델은 Git에서 제외되어 있으므로, 저장소를 clone한 뒤 아래 파일을 별도로 준비해야 합니다. 화면 이미지는 README에서 확인할 수 있습니다.

## 필요한 파일

| 위치 | 역할 |
|---|---|
| `data/raw/home_purchases.csv` | 고객별 주택 구매·거래 참조·재무 정보 |
| `data/raw/loans_raw.csv` | 개별 대출 최초 원금·잔액·상환 정보 |
| `data/raw/customers_preprocessed.csv` | 구매 고객의 전처리된 재무·현금흐름 |
| `data/raw/real_estate_detail_preprocessed.csv` | 부동산 상세와 거래 참조 정보 |
| `data/raw/customer_financial_profiles.csv` | 전체 고객 프로필 |
| `data/raw/customer_debt_summary.csv` | 전체 고객의 부채·월 상환 요약 |
| `data/raw/accounts.csv` | 고객별 계좌 잔액·상태 |
| `data/housing.sqlite` | CSV에서 생성한 서비스 DB |
| `models/home_loan_models.joblib` | 학습된 GBM과 전처리 메타데이터 |

고객 정보는 `customer_id`, 부동산 정보는 `real_asset_id`, 개별 대출은 `loan_id`를 기준으로 연결합니다. 상세 컬럼과 일치 검사는 `housing_app/source_data.py`, 화면별 사용처는 [데이터 매핑](implementation/data-mapping.md)에 있습니다.

## 기존 학습 모델로 실행

1. [README의 환경 설치](../README.md#빠른-시작-windows)를 진행합니다.
2. CSV 7개를 `data/raw/`, 기존 학습 파일을 `models/`에 배치합니다.
3. 이미 준비된 DB를 `data/housing.sqlite`에 배치하거나, 앱을 종료한 상태에서 아래 명령으로 CSV를 검증하고 DB를 생성합니다.

```powershell
.\side\Scripts\python.exe -m scripts.audit_data
.\side\Scripts\python.exe -m scripts.build_database
```

4. 프론트엔드를 빌드하고 `.env`를 설정한 뒤 `start.cmd`로 실행합니다. 실행 전 검사는 필요한 데이터·모델·빌드 파일을 확인하며, 누락된 파일을 임의로 생성하지 않습니다.

CSV 적재와 DB 생성은 모델을 재학습하지 않습니다. 새 모델을 만들려는 경우에만 `python -m scripts.train`을 사용합니다. 저장된 모델의 scikit-learn 버전은 `requirements.txt`와 맞춰야 합니다.

`data/chat_checkpoints.sqlite`는 실행 중 생성되는 대화 기록이며 배포용 데이터에 포함하지 않습니다. 네이버 좌표 캐시는 서비스 DB에 저장됩니다.

## GitHub 업로드 크기 확인

아래는 2026.10.12 로컬 파일 크기입니다. 단위는 MiB(1,048,576바이트)입니다.

| 파일 | 크기 |
|---|---:|
| `accounts.csv` | 9.21 MiB |
| `customer_debt_summary.csv` | 11.33 MiB |
| `customer_financial_profiles.csv` | 20.95 MiB |
| `customers_preprocessed.csv` | 24.84 MiB |
| `home_purchases.csv` | 38.15 MiB |
| `loans_raw.csv` | 8.63 MiB |
| `real_estate_detail_preprocessed.csv` | 6.44 MiB |
| **CSV 합계** | **119.55 MiB** |
| `housing.sqlite` | 190.47 MiB |
| `home_loan_models.joblib` | 1.25 MiB |

CSV는 각각 일반 Git push의 파일 크기 제한 안에 있습니다. DB는 100 MiB를 초과하므로 일반 Git push 대상이 될 수 없습니다. GitHub는 일반 Git 파일이 50 MiB를 초과하면 경고하고 100 MiB를 초과하면 차단합니다. 웹 브라우저 업로드 한도는 파일당 25 MiB이므로 가장 큰 CSV는 Git CLI가 필요합니다. [GitHub 공식 파일 크기 안내](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

전체 데이터를 배포하려면 CSV와 모델을 별도 다운로드로 제공하고 DB를 생성하거나, DB를 Git LFS·Release 첨부파일로 제공할 수 있습니다. 현재 저장소는 데이터·모델 제외 설정을 유지하며, 다운로드 파일은 게시되어 있지 않습니다.
