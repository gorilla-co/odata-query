use crate::ast::CommonExpr;
use crate::parser::literal::parse_literal;
use nom::combinator::map;
use nom::IResult;

pub fn parse(odata_query: &str) -> IResult<&str, CommonExpr> {
    (map(parse_literal, CommonExpr::Literal))(odata_query)
}
