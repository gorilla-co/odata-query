use crate::ast::CommonExpr;
use crate::parser::literal::parse_literal;
use crate::parser::name::parse_name;
use nom::branch::alt;
use nom::combinator::map;
use nom::IResult;

pub fn parse(odata_query: &str) -> IResult<&str, CommonExpr> {
    let literal = map(parse_literal, CommonExpr::Literal);
    let name = map(parse_name, CommonExpr::Name);

    alt((literal, name))(odata_query)
}
