"""
ground_truth_service.py
=======================
Service quản lý việc truy xuất và sử dụng Ground Truth data từ prq.ground_truth
một cách linh hoạt cho training và parser.

Tính năng:
- Truy xuất ground truth data với filter linh hoạt
- Join với administrative units để validate
- Cung cấp interface thống nhất cho training và parser
- Cache data để tối ưu performance
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func
import pandas as pd

from app.core.database import SessionLocal, GroundTruth, Ward, District, Province
from app.services.typesense_ground_truth_sync import POST_ADMIN_VERSION

logger = logging.getLogger(__name__)


class GroundTruthService:
    """Service quản lý Ground Truth data với các tính năng linh hoạt"""
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionLocal()
        self._should_close_session = session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session:
            self.session.close()
    
    def get_validated_addresses(
        self, 
        province_id: Optional[int] = None,
        district_id: Optional[int] = None,
        ward_id: Optional[int] = None,
        include_unvalidated: bool = True,
        source_system: Optional[str] = None,
        limit: Optional[int] = None,
        validate_admin_units: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Lấy danh sách địa chỉ Ground Truth với các filter
        
        Args:
            province_id: Filter theo province
            district_id: Filter theo district  
            ward_id: Filter theo ward
            include_unvalidated: Có bao gồm data chưa validate không
            source_system: Filter theo source (TYPESENSE, GOOGLE, MANUAL)
            limit: Giới hạn số lượng
            validate_admin_units: Có validate với admin units không
            
        Returns:
            List các địa chỉ ground truth
        """
        logger.info(f"Retrieving ground truth data with filters: province={province_id}, district={district_id}, ward={ward_id}")
        
        if validate_admin_units:
            # Join mat theo old_id + admin_version (post‑reform), thống nhất query prq.v_ground_truth_admin
            av = POST_ADMIN_VERSION
            query = self.session.query(GroundTruth)\
                .join(Ward, and_(
                    GroundTruth.ward_id == Ward.old_id,
                    Ward.is_deleted == False,
                    Ward.is_active == True,
                    Ward.admin_version == av,
                ))\
                .join(District, and_(
                    GroundTruth.district_id == District.old_id,
                    District.is_deleted == False,
                    District.is_active == True,
                    District.admin_version == av,
                ))\
                .join(Province, and_(
                    GroundTruth.province_id == Province.old_id,
                    Province.is_deleted == False,
                    Province.admin_version == av,
                ))
        else:
            query = self.session.query(GroundTruth)
        
        # Apply filters
        if province_id is not None:
            query = query.filter(GroundTruth.province_id == province_id)
        
        if district_id is not None:
            query = query.filter(GroundTruth.district_id == district_id)
            
        if ward_id is not None:
            query = query.filter(GroundTruth.ward_id == ward_id)
        
        if not include_unvalidated:
            query = query.filter(GroundTruth.is_validated == True)
        
        if source_system:
            query = query.filter(GroundTruth.source_system == source_system)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        # Execute and convert to dict
        results = []
        for gt in query.all():
            results.append({
                'id': gt.id,
                'address': gt.address,
                'old_address': gt.old_address,
                'address_eng': gt.address_eng,
                'province_id': gt.province_id,
                'district_id': gt.district_id,
                'ward_id': gt.ward_id,
                'latitude': gt.latitude,
                'longitude': gt.longitude,
                'popular': gt.popular,
                'source_system': gt.source_system,
                'is_validated': gt.is_validated,
                'data_quality_score': gt.data_quality_score
            })
        
        logger.info(f"Retrieved {len(results)} ground truth records")
        return results
    
    def get_corpus_addresses(
        self, 
        limit: Optional[int] = None,
        min_quality_score: Optional[float] = None,
        source_systems: Optional[List[str]] = None
    ) -> List[str]:
        """
        Lấy corpus địa chỉ chuẩn để training/similarity search
        
        Args:
            limit: Giới hạn số lượng
            min_quality_score: Score chất lượng tối thiểu
            source_systems: Danh sách source system cho phép
            
        Returns:
            List địa chỉ string
        """
        query = self.session.query(GroundTruth.address)\
            .filter(GroundTruth.address.isnot(None))\
            .filter(GroundTruth.address != '')
        
        if min_quality_score is not None:
            query = query.filter(GroundTruth.data_quality_score >= min_quality_score)
        
        if source_systems:
            query = query.filter(GroundTruth.source_system.in_(source_systems))
        
        # Distinct addresses only
        query = query.distinct()
        
        if limit:
            query = query.limit(limit)
        
        addresses = [row.address for row in query.all()]
        logger.info(f"Retrieved {len(addresses)} corpus addresses")
        return addresses
    
    def get_training_pairs(
        self,
        limit: Optional[int] = None,
        include_old_addresses: bool = True
    ) -> List[Tuple[str, str]]:
        """
        Lấy cặp địa chỉ (raw, normalized) để training
        
        Args:
            limit: Giới hạn số lượng
            include_old_addresses: Có bao gồm old_address không
            
        Returns:
            List of (raw_address, normalized_address) tuples
        """
        pairs = []
        
        query = self.session.query(GroundTruth)\
            .filter(GroundTruth.address.isnot(None))\
            .filter(GroundTruth.address != '')
        
        if limit:
            query = query.limit(limit)
        
        for gt in query.all():
            # Pair 1: old_address -> address (if available)
            if include_old_addresses and gt.old_address and gt.old_address != gt.address:
                pairs.append((gt.old_address, gt.address))
            
            # Pair 2: address -> address (for positive samples)
            pairs.append((gt.address, gt.address))
        
        logger.info(f"Generated {len(pairs)} training pairs")
        return pairs
    
    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê về Ground Truth data"""
        
        stats = {}
        
        # Total records
        stats['total_records'] = self.session.query(GroundTruth).count()
        
        # By source system
        source_stats = self.session.query(
            GroundTruth.source_system,
            func.count(GroundTruth.id).label('count')
        ).group_by(GroundTruth.source_system).all()
        
        stats['by_source'] = {row.source_system: row.count for row in source_stats}
        
        # Validation status
        validated_count = self.session.query(GroundTruth)\
            .filter(GroundTruth.is_validated == True).count()
        stats['validated_records'] = validated_count
        stats['validation_rate'] = validated_count / stats['total_records'] if stats['total_records'] > 0 else 0
        
        # Geographic distribution
        province_stats = self.session.query(
            GroundTruth.province_id,
            func.count(GroundTruth.id).label('count')
        ).filter(GroundTruth.province_id.isnot(None))\
         .group_by(GroundTruth.province_id)\
         .order_by(func.count(GroundTruth.id).desc())\
         .limit(10).all()
        
        stats['top_provinces'] = [{'province_id': row.province_id, 'count': row.count} for row in province_stats]
        
        # Quality distribution
        quality_stats = self.session.query(
            func.avg(GroundTruth.data_quality_score).label('avg_quality'),
            func.min(GroundTruth.data_quality_score).label('min_quality'),
            func.max(GroundTruth.data_quality_score).label('max_quality')
        ).filter(GroundTruth.data_quality_score.isnot(None)).first()
        
        if quality_stats.avg_quality is not None:
            stats['quality_scores'] = {
                'average': float(quality_stats.avg_quality),
                'minimum': float(quality_stats.min_quality),
                'maximum': float(quality_stats.max_quality)
            }
        
        return stats
    
    def update_quality_score(self, ground_truth_id: int, quality_score: float, notes: str = None) -> bool:
        """
        Cập nhật quality score cho một record
        
        Args:
            ground_truth_id: ID của ground truth record
            quality_score: Score từ 0.0 đến 1.0
            notes: Ghi chú
            
        Returns:
            True if successful
        """
        try:
            gt = self.session.query(GroundTruth).filter(GroundTruth.id == ground_truth_id).first()
            if not gt:
                logger.warning(f"Ground truth record {ground_truth_id} not found")
                return False
            
            gt.data_quality_score = quality_score
            if notes:
                gt.validation_notes = notes
            
            self.session.commit()
            logger.info(f"Updated quality score for record {ground_truth_id}: {quality_score}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update quality score: {str(e)}")
            self.session.rollback()
            return False
    
    def mark_as_validated(self, ground_truth_ids: List[int], notes: str = None) -> int:
        """
        Đánh dấu các record đã được validate
        
        Args:
            ground_truth_ids: Danh sách ID cần validate
            notes: Ghi chú validation
            
        Returns:
            Số lượng record được cập nhật
        """
        try:
            updated_count = self.session.query(GroundTruth)\
                .filter(GroundTruth.id.in_(ground_truth_ids))\
                .update({
                    GroundTruth.is_validated: True,
                    GroundTruth.validation_notes: notes
                }, synchronize_session=False)
            
            self.session.commit()
            logger.info(f"Marked {updated_count} records as validated")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to mark records as validated: {str(e)}")
            self.session.rollback()
            return 0


# Convenience functions
def get_ground_truth_service(session: Optional[Session] = None) -> GroundTruthService:
    """Factory function để tạo GroundTruthService"""
    return GroundTruthService(session)


def get_corpus_for_training(limit: Optional[int] = None) -> List[str]:
    """Shortcut để lấy corpus cho training"""
    with get_ground_truth_service() as service:
        return service.get_corpus_addresses(
            limit=limit,
            source_systems=['TYPESENSE', 'GOOGLE'],  # Ưu tiên data từ external sources
            min_quality_score=0.7  # Chỉ lấy data chất lượng cao
        )


def get_training_data(limit: Optional[int] = None) -> pd.DataFrame:
    """Shortcut để lấy training data dưới dạng DataFrame"""
    with get_ground_truth_service() as service:
        addresses = service.get_validated_addresses(
            limit=limit,
            include_unvalidated=False  # Chỉ lấy data đã validate
        )
        return pd.DataFrame(addresses)