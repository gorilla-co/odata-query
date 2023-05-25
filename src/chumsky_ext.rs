use chumsky::prelude::*;

/// A case-insensitive variant of chumsky::text::keyword
pub fn keyword_ignore_ascii_case(
    keyword: &'static str,
) -> impl Parser<char, (), Error = Simple<char>> {
    text::ident().try_map(move |s: String, span| {
        if s.eq_ignore_ascii_case(keyword) {
            Ok(())
        } else {
            Err(Simple::expected_input_found(span, None, None))
        }
    })
}
