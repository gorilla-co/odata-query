use crate::ast::Name;
use nom::branch::alt;
use nom::bytes::complete::{is_not, tag, tag_no_case, take_while, take_while_m_n};
use nom::combinator::{cut, into, map, map_res, opt, recognize, value, verify};
use nom::sequence::{delimited, pair, preceded, terminated, tuple};
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

pub fn parse_name(inp: &str) -> IResult<&str, Name> {
    let identifier = map(parse_identifier, Name::Identifier);

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
    }
}
