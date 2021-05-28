# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2021-05-28

### Changed
- Raise a new `InvalidFieldException` if a field in a query doesn't exist.

### Fixed
- Allow `AliasRewriter` to recurse into `Attribute` nodes, in order to replace
  nodes in the `Attribute`'s ownership chain.

## [0.3.0] - 2021-05-17

### Added
- Added `NodeTransformers`, which are like `NodeVisitors` but replace visited
  nodes with the returned value.
- Initial API documentation.

### Changed
- The AstTo{ORMQuery} visitors for SQLAlchemy and Django now have the same
  interface.
- AstToDjangoQVisitor now builds subqueries for `any()/all()` itself, instead
  of relying on `SubQueryToken`s and a seperate visitor.
- Made all AST Nodes `frozen` (read-only), so they can be hashed.
- Replaced `field_mapping` on the ORM visitors with a more general
  `AliasRewriter` based on the new `NodeTransformers`.
- Refactored `IdentifierStripper` to use the new `NodeTransformers`.

## [0.2.0] - 2021-05-05

### Added
- Transform OData queries to SQLAlchemy expressions with the new
  AstToSqlAlchemyClauseVisitor.

### Changed
- Don't write a debugfile for the parser by default.

## [0.1.0] - 2021-03-12

### Added
- Initial split to seperate package.
