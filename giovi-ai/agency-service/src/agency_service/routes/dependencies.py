from fastapi import Header, HTTPException, status


def require_agency_id(x_agency_id: str = Header(alias="X-Agency-Id")) -> str:
    if not x_agency_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Agency-Id header",
        )
    return x_agency_id

