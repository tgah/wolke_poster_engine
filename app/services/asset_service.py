"""Asset storage service."""
from typing import Optional
from uuid import UUID
from pathlib import Path
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session
from PIL import Image
import io

from app.models.asset import Asset, AssetType, StorageBackend
from app.config import get_settings

settings = get_settings()


class AssetService:
    """Handle asset storage and retrieval."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_asset(
        self,
        file_bytes: bytes,
        asset_type: AssetType,
        company_id: UUID,
        user_id: Optional[UUID] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        mime_type: str = "image/png"
    ) -> Asset:
        """
        Save asset to storage backend and create database record.
        """
        # Get image dimensions if not provided
        if width is None or height is None:
            try:
                img = Image.open(io.BytesIO(file_bytes))
                width, height = img.size
            except Exception:
                pass
        
        # Generate unique filename
        file_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        extension = mime_type.split("/")[-1]
        filename = f"{asset_type.value}_{timestamp}_{file_hash}.{extension}"
        
        # Save to storage
        if settings.STORAGE_BACKEND == "local":
            storage_path = self._save_local(filename, file_bytes, asset_type)
        elif settings.STORAGE_BACKEND == "s3":
            storage_path = self._save_s3(filename, file_bytes, asset_type)
        else:
            raise ValueError(f"Unknown storage backend: {settings.STORAGE_BACKEND}")
        
        # Create asset record
        asset = Asset(
            company_id=company_id,
            type=asset_type,
            storage_backend=StorageBackend(settings.STORAGE_BACKEND),
            path=storage_path,
            width=width,
            height=height,
            mime_type=mime_type,
            file_size=len(file_bytes),
            created_by_user_id=user_id
        )
        
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        
        return asset
    
    def _save_local(
        self,
        filename: str,
        file_bytes: bytes,
        asset_type: AssetType
    ) -> str:
        """Save to local filesystem."""
        # Create directory structure
        base_path = Path(settings.STORAGE_BASE_PATH)
        type_dir = base_path / asset_type.value
        type_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = type_dir / filename
        file_path.write_bytes(file_bytes)
        
        # Return relative path
        return f"{asset_type.value}/{filename}"
    
    def _save_s3(
        self,
        filename: str,
        file_bytes: bytes,
        asset_type: AssetType
    ) -> str:
        """Save to S3 (implementation depends on boto3)."""
        import boto3
        
        s3_client = boto3.client(
            's3',
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY
        )
        
        key = f"{asset_type.value}/{filename}"
        
        s3_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType="image/png"
        )
        
        return key
    
    def get_asset_url(self, asset: Asset) -> str:
        """Generate public URL for asset."""
        if asset.storage_backend == StorageBackend.LOCAL:
            return f"{settings.STORAGE_BASE_URL}/{asset.path}"
        elif asset.storage_backend == StorageBackend.S3:
            return f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{asset.path}"
        else:
            raise ValueError(f"Unknown storage backend: {asset.storage_backend}")
