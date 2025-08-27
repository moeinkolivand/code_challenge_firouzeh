from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from infrastructure.databases.postgres import DatabaseConnector
from models.url_shortener import UrlShorter



class UrlShorterRepository:
    def __init__(self, db_connector: DatabaseConnector):
        self.db_connector = db_connector

    def create(self, original_url: str, shorted_url: Optional[str] = None) -> Optional[UrlShorter]:
        try:
            with self.db_connector.get_session() as session:
                url_shorter = UrlShorter(
                    original_url=original_url,
                    shorted_url=shorted_url
                )
                session.add(url_shorter)
                session.commit()
                return url_shorter
        except IntegrityError as e:
            raise ValueError(f"URL shorter already exists or constraint violation: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create URL shorter: {e}")
    
    def get_by_id(self, url_id: str) -> Optional[UrlShorter]:
        try:
            with self.db_connector.get_session() as session:
                stmt = select(UrlShorter).where(UrlShorter.id == url_id)
                return session.execute(stmt).scalar_one_or_none()
        except Exception as e:
            raise RuntimeError(f"Failed to get URL shorter by ID: {e}")
    
    def get_by_shorted_url(self, shorted_url: str) -> Optional[UrlShorter]:
        try:
            with self.db_connector.get_session() as session:
                stmt = select(UrlShorter).where(UrlShorter.shorted_url == shorted_url)
                return session.execute(stmt).scalar_one_or_none()
        except Exception as e:
            raise RuntimeError(f"Failed to get URL shorter by shortened URL: {e}")
    
    def get_by_original_url(self, original_url: str) -> List[UrlShorter]:
        try:
            with self.db_connector.get_session() as session:
                stmt = select(UrlShorter).where(UrlShorter.original_url == original_url)
                return session.execute(stmt).scalars().all()
        except Exception as e:
            raise RuntimeError(f"Failed to get URL shorteners by original URL: {e}")
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[UrlShorter]:
        try:
            with self.db_connector.get_session() as session:
                stmt = select(UrlShorter).offset(offset).limit(limit)
                return session.execute(stmt).scalars().all()
        except Exception as e:
            raise RuntimeError(f"Failed to get all URL shorteners: {e}")

    def exists_by_shorted_url(self, shorted_url: str) -> bool:
        return self.get_by_shorted_url(shorted_url) is not None

    def update(self, url_id: str, **kwargs) -> Optional[UrlShorter]:
        try:
            with self.db_connector.get_session() as session:
                url_shorter = session.get(UrlShorter, url_id)
                if not url_shorter:
                    return None
                for field, value in kwargs.items():
                    if hasattr(url_shorter, field):
                        setattr(url_shorter, field, value)
                
                session.flush()
                session.refresh(url_shorter)
                return url_shorter
        except IntegrityError as e:
            raise ValueError(f"Update constraint violation: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to update URL shorter: {e}")


# # Usage example
# def example_usage():
#     """Example of how to use the repository"""
#     from your_database_module import create_database_connector
    

#     db_connector = create_database_connector(
#         backend="postgresql",
#         host="localhost",
#         username="your_username",
#         password="your_password",
#         database="your_database"
#     )
    

#     repo = UrlShorterRepository(db_connector)
    
#     try:
#         url_shorter = repo.create(
#             original_url="https://www.example.com/very/long/url",
#             shorted_url="abc123"
#         )
#         print(f"Created: {url_shorter.id}")
        

#         found = repo.get_by_shorted_url("abc123")
#         if found:
#             print(f"Original URL: {found.original_url}")
        

#         updated = repo.update(url_shorter.id, original_url="https://updated.com")
#         print(f"Updated: {updated.original_url}")
        

#         all_urls = repo.get_all(limit=10, offset=0)
#         print(f"Total found: {len(all_urls)}")
        
#     except Exception as e:
#         print(f"Error: {e}")
