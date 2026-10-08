# 배포 및 의존성 관리

## 의존성 정책

Python 3.12.14에서 검증했습니다. `requirements.txt`는 FastAPI 실행용, `requirements-dev.txt`는 테스트·Ruff와 이전 Streamlit UI 확인용입니다. 두 파일 모두 하위 의존성 버전과 배포 패키지 SHA-256 해시를 고정합니다. 설치는 `--require-hashes`를 사용합니다. Windows와 Linux를 대상으로 universal 잠금을 생성했습니다. 잠금은 호환 가능한 설치 재현을 위한 것이며 취약점이 없음을 보장하는 검사는 아닙니다.

일반 설치는 `setup.cmd dev`입니다. 불필요해진 패키지까지 제거해 잠금 파일과 정확히 맞추려면 uv를 사용할 수 있습니다.

```powershell
uv pip sync requirements-dev.txt --python side\Scripts\python.exe --require-hashes
```

직접 의존성 변경 후 기존 하위 버전을 최대한 유지해 재잠금합니다. 의도적으로 상위 버전을 바꿀 때는 충돌하는 기존 constraint를 먼저 별도 작업에서 검토하세요.

```powershell
uv pip compile requirements.in --constraint requirements.txt --universal --python-version 3.12 --generate-hashes --output-file requirements.txt
uv pip compile requirements-dev.in --constraint requirements.txt --universal --python-version 3.12 --generate-hashes --output-file requirements-dev.txt
```

scikit-learn 1.9.1로 저장된 모델을 사용합니다. 설치 성공만으로 모델 버전 업그레이드 검증을 대신할 수 없습니다.

## Docker 실행

1. Docker Desktop에서 Linux 컨테이너 엔진을 시작합니다.
2. 현재 PC의 `.env`, `data/`, `models/`를 유지합니다. 새 서버에는 별도로 안전하게 전달합니다.
3. 기존 로컬 앱을 종료해 8501 포트를 비웁니다.
4. 아래 명령을 실행합니다.

```powershell
docker compose --env-file .env.example config --quiet
docker compose --env-file .env.example up --build -d
docker compose --env-file .env.example ps
docker compose --env-file .env.example logs --tail 100 web
```

`--env-file .env.example`은 Compose의 변수 치환에만 사용합니다. 실제 `.env`는 컨테이너의 `/app/.env`에 읽기 전용으로 연결하므로 Compose가 키의 `$` 문자를 치환하지 않습니다. 예시에는 실제 키를 넣지 마세요. 실제 `.env`를 출력하는 `docker compose config` 결과를 공유하지 마세요.

이미지는 Node.js 빌드 단계에서 React 화면을 생성하고 최종 Python 단계에는 실행 코드·완성된 화면·검증 보고서만 포함합니다. API 키, raw CSV, DB, 모델, 가상환경은 빌드 컨텍스트에서 제외합니다. 컨테이너는 UID/GID 10001의 일반 사용자로 실행되며 루트 파일시스템은 읽기 전용입니다. 지도 캐시 저장 때문에 `/app/data`만 영속 쓰기가 필요합니다. 모델은 읽기 전용 마운트입니다. Linux 서버에서는 UID 10001이 DB와 data 디렉터리에 쓰고 `.env`·모델·CSV를 읽을 수 있게 파일 권한을 맞춰야 합니다.

Windows 절대경로를 넣은 `DATABASE_PATH` 또는 `HOME_LOAN_DATA_DIR` 설정은 Linux 컨테이너에서 사용할 수 없습니다. 서버용 설정에서는 기본 경로를 사용하거나 `/app/data/housing.sqlite`, `/app/data/raw`로 지정합니다. 로컬 키 파일을 덮어쓰지 말고 서버 설정을 별도로 관리하세요.

기본 호스트 포트는 `127.0.0.1:8501`에만 연결됩니다. 같은 Wi-Fi 테스트가 필요하면 해당 PowerShell 세션에서 `$env:BIND_ADDRESS='0.0.0.0'`를 설정하고 Compose를 실행합니다. 방화벽·네이버 허용 URL을 함께 확인하세요. 로컬 Python 실행의 대안으로 Docker를 사용하며 둘을 같은 포트에서 동시에 실행하지 않습니다.

종료: `docker compose --env-file .env.example down`. 데이터는 호스트 폴더에 남습니다. 재시작: `docker compose --env-file .env.example restart web`. 헬스체크는 FastAPI의 `/api/health` 응답만 검사하며 외부 API 정상 여부는 검사하지 않습니다.

## 인터넷 공개 전 남은 항목

현재 앱에 사용자 로그인과 사용자별 API 호출량 제한은 없습니다. 공개 배포 전 접근을 인증 프록시/SSO로 제한하고 요청 한도·API 비용 예산을 설정해야 합니다. 대화 이력은 브라우저 메모리에 있고 SQLite 지도 캐시는 단일 인스턴스를 전제로 합니다. 다중 인스턴스 확장은 DB·세션 저장 구조를 먼저 바꿔야 합니다.

서버 볼륨 백업에는 DB, 원본 CSV, 모델, 생성 보고서를 포함합니다. API 키는 별도 비밀 설정으로 관리합니다. 배포 시에는 실제 OpenAI 모델 접근 권한, 네이버 Dynamic Map/Geocoding 및 허용 URL, 모바일 화면을 확인해야 합니다.
