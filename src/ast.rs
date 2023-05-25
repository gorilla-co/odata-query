#[derive(Debug, PartialEq, Clone)]
pub enum Literal {
    // primitiveLiteral
    Null,
    Boolean(bool),
    Date(String),
    DateTimeOffset(String),
    Time(String),
    Float(f64), // decimal, double, single
    GUID(String),
    Integer(i64), // sbyte, byte, int16, int32 ,int64
    String(String),
    Duration(String),
    Binary(Box<[u8]>),
}

#[derive(Debug, PartialEq, Clone)]
pub enum CommonExpr {
    Literal(Literal),
}
