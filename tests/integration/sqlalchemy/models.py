from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


author_blogpost = Table(
    "author_blogpost",
    Base.metadata,
    Column("author_id", Integer, ForeignKey("author.id")),
    Column("blogpost_id", Integer, ForeignKey("blogpost.id")),
)


class Author(Base):
    __tablename__ = "author"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    blogposts = relationship(
        "BlogPost", back_populates="authors", secondary=author_blogpost
    )
    comments = relationship("Comment", back_populates="author")


class BlogPost(Base):
    __tablename__ = "blogpost"

    id = Column(Integer, primary_key=True)
    published_at = Column(DateTime, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)

    authors = relationship(
        "Author", back_populates="blogposts", secondary=author_blogpost
    )
    comments = relationship("Comment", back_populates="blogpost")


class Comment(Base):
    __tablename__ = "comment"

    id = Column(Integer, primary_key=True)
    content = Column(Text)

    author_id = Column(Integer, ForeignKey("author.id"))
    author = relationship("Author", back_populates="comments")
    blogpost_id = Column(Integer, ForeignKey("blogpost.id"))
    blogpost = relationship("BlogPost", back_populates="comments")
