"""Normalize export labels, retaining raw addresses separately."""

SEOUL_GU = "강남구 강동구 강북구 강서구 관악구 광진구 구로구 금천구 노원구 도봉구 동대문구 동작구 마포구 서대문구 서초구 성동구 성북구 송파구 양천구 영등포구 용산구 은평구 종로구 중구 중랑구".split()


def normalize_region(sido, district):
    sido = str(sido).strip()
    parts = str(district).split()
    cities = (
        "고양",
        "성남",
        "수원",
        "안산",
        "안양",
        "용인",
        "전주",
        "천안",
        "청주",
        "창원",
        "포항",
    )
    if parts:
        for city in cities:
            if (
                parts[0].startswith(city)
                and parts[0].endswith("구")
                and not parts[0].startswith(city + "시")
            ):
                parts = [city + "시", parts[0][len(city) :]] + parts[1:]
                break
    district = " ".join(p for p in parts if p.endswith(("시", "군", "구")))
    if sido == "전남광주통합특별시":
        sido = (
            "광주광역시" if district in {"광산구", "동구", "서구", "남구", "북구"} else "전라남도"
        )
    sido = {"전라북도": "전북특별자치도", "강원도": "강원특별자치도"}.get(sido, sido)
    return sido, district or ("세종시 전체" if sido == "세종특별자치시" else "확인 불가")


def split_region(text):
    parts = str(text).split(maxsplit=1)
    return normalize_region(parts[0], parts[1] if len(parts) > 1 else "")
