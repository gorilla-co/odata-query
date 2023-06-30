use pyo3::prelude::*;

mod ast;
mod parser;
#[cfg(test)]
mod test_util;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn parse_odata(odata_query: &str) -> PyResult<bool> {
    let ast = parser::expr::parse(odata_query);
    println!("{:?}", ast);
    Ok(true)
}

/// A Python module implemented in Rust.
#[pymodule]
fn _odata_query(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_odata, m)?)?;
    Ok(())
}
