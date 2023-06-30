use time::{Date, Duration, OffsetDateTime, Time};

/// primitiveLiteral
#[derive(Debug, PartialEq, Clone)]
pub enum Literal {
    Null,
    Boolean(bool),
    Date(Date),
    DateTimeOffset(OffsetDateTime),
    Time(Time),
    /// decimal, double, single
    Float(f64),
    GUID(String),
    /// sbyte, byte, int16, int32, int64
    Integer(i64),
    String(String),
    Duration(Duration),
    Binary(Vec<u8>),
}

#[derive(Debug, PartialEq, Clone)]
pub enum Name {
    Identifier(String),
    Qualified(Vec<String>),
}

#[derive(Debug, PartialEq, Clone)]
pub enum CommonExpr {
    Literal(Literal),
    Name(Name),
}
