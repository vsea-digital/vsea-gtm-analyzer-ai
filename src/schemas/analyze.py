from pydantic import BaseModel, Field, HttpUrl


class DocumentAnalyzeRequest(BaseModel):
    gcs_uri: str = Field(
        ..., description="GCS URI returned by /upload, e.g. gs://bucket/path"
    )
    market: str
    industry: str


class UrlAnalyzeRequest(BaseModel):
    url: HttpUrl
    market: str
    industry: str
