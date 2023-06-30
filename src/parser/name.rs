use crate::ast::Name;
use nom::branch::alt;
use nom::bytes::complete::{take_while, take_while_m_n};
use nom::character::complete::char;
use nom::combinator::{map, recognize};
use nom::multi::separated_list1;
use nom::sequence::tuple;
use nom::IResult;

fn _is_odata_id_leading(inp: char) -> bool {
    inp.is_alphabetic() || inp == '_'
}

fn _is_odata_id(inp: char) -> bool {
    inp.is_alphanumeric() || inp == '_'
}

pub fn parse_identifier(inp: &str) -> IResult<&str, String> {
    let parser = recognize(tuple((
        take_while_m_n(1, 1, _is_odata_id_leading),
        take_while(_is_odata_id),
    )));

    map(parser, |s: &str| s.to_string())(inp)
}

pub fn parse_optionally_qualified(inp: &str) -> IResult<&str, Vec<String>> {
    separated_list1(char('.'), parse_identifier)(inp)
}

pub fn parse_name(inp: &str) -> IResult<&str, Name> {
    let identifier = map(
        parse_optionally_qualified,
        |parts: Vec<String>| match parts.len() {
            1 => Name::Identifier(parts[0].clone()),
            _ => Name::Qualified(parts),
        },
    );

    alt((identifier,))(inp)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_util::assert_parsed_to;

    #[test]
    fn parse_identifier() {
        assert_parsed_to(
            parse_name("variable"),
            Name::Identifier("variable".to_string()),
        );
        assert_parsed_to(
            parse_name("_var123"),
            Name::Identifier("_var123".to_string()),
        );
    }

    #[test]
    fn parse_qualified() {
        assert_parsed_to(
            parse_name("my.var"),
            Name::Qualified(vec!["my".to_string(), "var".to_string()]),
        );
    }
}
