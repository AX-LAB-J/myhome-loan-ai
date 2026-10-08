# 배포 안내 (GitHub · Docker · AWS)

구성: **GitHub**에는 코드만, **ECR**에는 Docker 이미지, **EC2 한 대**에는 데이터·모델·키를 둡니다.
SQLite 파일 DB를 쓰는 단일 인스턴스 구조이므로 ECS/App Runner보다 EC2 + Docker Compose가 단순하고 저렴합니다.

```text
PC ──git push──▶ GitHub (코드, CI: 테스트·빌드 확인)
PC ──push-image.ps1──▶ ECR (이미지)
PC ──upload-files.ps1──▶ EC2 /opt/housing (.env, data/, models/)
EC2: Caddy(80/443) ──▶ web 컨테이너(8501) ──▶ /opt/housing/data, models
```

## 1. GitHub

`.gitignore`가 `.env`, `data/`, `models/`, `side/`, `archive/`, 빌드 결과를 제외합니다. 비공개 저장소를 만든 뒤:

```powershell
git remote add origin https://github.com/<계정>/<저장소>.git
git push -u origin main
```

`.github/workflows/ci.yml`이 push마다 Ruff·pytest·프론트엔드 빌드·Docker 빌드를 확인합니다. 비공개 데이터가 필요한 테스트(`@pytest.mark.data`)는 CI에서 자동으로 건너뜁니다.

## 2. 로컬 Docker 확인

Docker Desktop을 켜고 기존 `start.cmd` 서버를 끈 뒤(같은 8501 포트 사용):

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --tail 100 web
docker compose down
```

이미지에는 코드와 빌드된 화면만 들어 있고, `.env`(읽기 전용)·`data/`·`models/`(읽기 전용)는 실행할 때 연결합니다. 컨테이너는 UID 10001 일반 사용자, 읽기 전용 루트 파일시스템으로 실행됩니다. 시작 시 `scripts.check`가 필요한 파일을 확인하고, `/api/health`가 헬스체크입니다.

## 3. AWS 준비 (한 번만)

1. 루트 계정 MFA, 작업용 IAM 사용자, Billing → Budgets 월 예산 알림, 리전은 서울(ap-northeast-2).
2. PC에 AWS CLI 설치 후 `aws configure`.
3. EC2 인스턴스 생성
   - Amazon Linux 2023, **t3.small**(2GB, 실측 메모리 약 320MB) 이상, gp3 30GB
   - IAM 역할: `AmazonEC2ContainerRegistryReadOnly` 정책 연결 (ECR에서 이미지를 받기 위해)
   - 보안 그룹: SSH 22는 **내 IP만**, HTTP 80·HTTPS 443 허용
   - Elastic IP 연결

## 4. 배포

PC에서 (PowerShell, 프로젝트 폴더):

```powershell
powershell -ExecutionPolicy Bypass -File deploy\push-image.ps1
powershell -ExecutionPolicy Bypass -File deploy\upload-files.ps1 -Server <Elastic IP> -Key <키.pem 경로>
```

EC2에서 (`ssh -i <키.pem> ec2-user@<Elastic IP>`):

```bash
cd /opt/housing
bash ec2-setup.sh                  # 처음 한 번: Docker·Compose 설치, 2GB 스왑. 끝나면 다시 로그인
cp deploy.env.example deploy.env   # APP_IMAGE를 push-image.ps1이 알려준 주소로 수정
bash update.sh
```

브라우저에서 `http://<Elastic IP>`로 접속합니다. 네이버 클라우드 콘솔의 Maps 서비스 URL에 이 주소(나중에는 도메인)를 등록해야 지도가 나옵니다.

**코드만 바뀐 경우:** PC에서 `push-image.ps1` → EC2에서 `bash update.sh`. 데이터가 바뀌지 않았다면 `upload-files.ps1 -SkipData`로 설정 파일만 올립니다.

## 5. 도메인·HTTPS

도메인의 A 레코드를 Elastic IP로 지정하고 `deploy.env`의 `SITE_ADDRESS`를 도메인으로 바꾼 뒤 `bash update.sh`. Caddy가 Let's Encrypt 인증서를 자동으로 발급·갱신합니다.

## 운영 메모

- **비용:** 사용하지 않을 때 EC2를 중지하면 컴퓨팅 요금이 멈춥니다(EBS·Elastic IP는 과금). OpenAI 비용은 OpenAI 콘솔의 사용 한도로 관리합니다.
- **OpenAI 사용량:** 서버 로그에 대화마다 `chat thread=… calls=… input_tokens=… cached=… output_tokens=…`가 남습니다. `docker compose -f compose.aws.yaml logs web | grep "chat thread"`.
- **동시 대화:** `.env`의 `CHAT_MAX_CONCURRENCY`(기본 4)를 넘는 요청은 대기합니다. 이전 대화는 `CHAT_HISTORY_TURNS`(기본 6)턴까지만 모델에 다시 보냅니다. `MODEL_REASONING_EFFORT`(예: `low`)로 추론 강도를 낮춰 속도·비용을 줄일 수 있습니다.
- **백업:** `/opt/housing/data`(DB·지도 캐시·대화 기록)를 EBS 스냅샷으로 백업합니다.
- **확장 한계:** SQLite와 메모리 캐시는 인스턴스 1대를 전제로 합니다. 여러 대로 늘리려면 DB를 RDS 등으로 옮겨야 합니다.

## 의존성 관리

`requirements.in`(실행)과 `requirements-dev.in`(테스트·Ruff)을 고친 뒤 해시 잠금 파일을 다시 만듭니다. Windows·Linux 공용(universal) 잠금입니다.

```powershell
uv pip compile requirements.in --constraint requirements.txt --universal --python-version 3.12 --generate-hashes --output-file requirements.txt
uv pip compile requirements-dev.in --constraint requirements.txt --universal --python-version 3.12 --generate-hashes --output-file requirements-dev.txt
uv pip sync requirements-dev.txt --python side\Scripts\python.exe --require-hashes
```

저장된 모델은 scikit-learn 1.9.1로 학습되었습니다. scikit-learn·numpy 버전을 바꾸면 `scripts.check`가 실패하므로 재학습(`python -m scripts.train`)이 필요합니다.
