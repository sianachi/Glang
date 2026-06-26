from enum import Enum, auto


class TokenType(Enum):
    # --- Literals ---
    INT_LIT    = auto()  # 42, 0xFF, 0b1010, 1_000_000
    FLOAT_LIT  = auto()  # 3.14, 1.0e-5
    CHAR_LIT   = auto()  # 'a', '\n', '\x41'
    STRING_LIT = auto()  # "hello\tworld"

    # --- Identifier ---
    IDENT = auto()  # foo, myVar, _count

    # --- Keywords (31) ---
    # Types
    KW_INT       = auto()  # int
    KW_FLOAT     = auto()  # float
    KW_BOOL      = auto()  # bool
    KW_CHAR      = auto()  # char
    KW_BYTE      = auto()  # byte
    KW_STRING    = auto()  # string
    KW_VOID      = auto()  # void
    KW_VAR       = auto()  # var
    # Boolean literals
    KW_TRUE      = auto()  # true
    KW_FALSE     = auto()  # false
    # Null
    KW_NULL      = auto()  # null
    # OOP
    KW_CLASS     = auto()  # class
    KW_INTERFACE = auto()  # interface
    KW_EXTENDS   = auto()  # extends
    KW_IMPLEMENTS= auto()  # implements
    KW_THIS      = auto()  # this
    KW_SUPER     = auto()  # super
    KW_NEW       = auto()  # new
    KW_DELETE    = auto()  # delete
    KW_STATIC    = auto()  # static
    # Memory
    KW_ALLOC     = auto()  # alloc
    KW_FREE      = auto()  # free
    KW_MANAGED   = auto()  # managed (GC-managed class modifier)
    # Control flow
    KW_IF        = auto()  # if
    KW_ELSE      = auto()  # else
    KW_WHILE     = auto()  # while
    KW_FOR       = auto()  # for
    KW_DO        = auto()  # do
    KW_FOREACH   = auto()  # foreach
    KW_IN        = auto()  # in
    KW_BREAK     = auto()  # break
    KW_CONTINUE  = auto()  # continue
    KW_RETURN    = auto()  # return
    # Module
    KW_IMPORT    = auto()  # import
    # Function pointer type
    KW_FN        = auto()  # fn
    # Enum
    KW_ENUM      = auto()  # enum

    KW_NAMESPACE = auto()  # namespace
    KW_USING     = auto()  # using
    # Qualifiers / visibility
    KW_CONST     = auto()  # const
    KW_PRIVATE   = auto()  # private
    KW_PROTECTED = auto()  # protected
    KW_PUBLIC    = auto()  # public
    KW_MODIFIER  = auto()  # modifier
    # Exceptions
    KW_TRY       = auto()  # try
    KW_CATCH     = auto()  # catch
    KW_THROW     = auto()  # throw

    # --- Arithmetic operators ---
    PLUS    = auto()  # +
    MINUS   = auto()  # -
    STAR    = auto()  # *  (also pointer type / dereference)
    AT      = auto()  # @  (managed handle type, e.g. Foo@)
    SLASH   = auto()  # /
    PERCENT = auto()  # %

    # --- Bitwise operators ---
    AMP    = auto()  # &  (also address-of)
    PIPE   = auto()  # |
    CARET  = auto()  # ^
    TILDE  = auto()  # ~
    LSHIFT = auto()  # <<
    RSHIFT = auto()  # >>

    # --- Logical operators ---
    AND  = auto()  # &&
    OR   = auto()  # ||
    BANG = auto()  # !

    # --- Comparison operators ---
    EQ  = auto()  # ==
    NEQ = auto()  # !=
    LT  = auto()  # <
    LTE = auto()  # <=
    GT  = auto()  # >
    GTE = auto()  # >=

    # --- Assignment operators ---
    ASSIGN         = auto()  # =
    PLUS_ASSIGN    = auto()  # +=
    MINUS_ASSIGN   = auto()  # -=
    STAR_ASSIGN    = auto()  # *=
    SLASH_ASSIGN   = auto()  # /=
    PERCENT_ASSIGN = auto()  # %=
    AMP_ASSIGN     = auto()  # &=
    PIPE_ASSIGN    = auto()  # |=
    CARET_ASSIGN   = auto()  # ^=
    LSHIFT_ASSIGN  = auto()  # <<=
    RSHIFT_ASSIGN  = auto()  # >>=

    # --- Increment / Decrement ---
    PLUS_PLUS   = auto()  # ++
    MINUS_MINUS = auto()  # --

    # --- Nullable / null-coalescing ---
    QUESTION          = auto()  # ?
    QUESTION_QUESTION = auto()  # ??

    # --- Punctuation ---
    LBRACE    = auto()  # {
    RBRACE    = auto()  # }
    LPAREN    = auto()  # (
    RPAREN    = auto()  # )
    LBRACKET  = auto()  # [
    RBRACKET  = auto()  # ]
    SEMICOLON = auto()  # ;
    COMMA     = auto()  # ,
    DOT       = auto()  # .
    ARROW     = auto()  # ->
    COLON     = auto()  # :
    COLONCOLON = auto() # ::

    # --- Special ---
    EOF = auto()  # end of input


KEYWORDS: dict[str, TokenType] = {
    "int":        TokenType.KW_INT,
    "float":      TokenType.KW_FLOAT,
    "bool":       TokenType.KW_BOOL,
    "char":       TokenType.KW_CHAR,
    "byte":       TokenType.KW_BYTE,
    "string":     TokenType.KW_STRING,
    "void":       TokenType.KW_VOID,
    "var":        TokenType.KW_VAR,
    "true":       TokenType.KW_TRUE,
    "false":      TokenType.KW_FALSE,
    "null":       TokenType.KW_NULL,
    "class":      TokenType.KW_CLASS,
    "interface":  TokenType.KW_INTERFACE,
    "extends":    TokenType.KW_EXTENDS,
    "implements": TokenType.KW_IMPLEMENTS,
    "this":       TokenType.KW_THIS,
    "super":      TokenType.KW_SUPER,
    "new":        TokenType.KW_NEW,
    "delete":     TokenType.KW_DELETE,
    "static":     TokenType.KW_STATIC,
    "alloc":      TokenType.KW_ALLOC,
    "free":       TokenType.KW_FREE,
    "managed":    TokenType.KW_MANAGED,
    "if":         TokenType.KW_IF,
    "else":       TokenType.KW_ELSE,
    "while":      TokenType.KW_WHILE,
    "for":        TokenType.KW_FOR,
    "do":         TokenType.KW_DO,
    "foreach":    TokenType.KW_FOREACH,
    "in":         TokenType.KW_IN,
    "break":      TokenType.KW_BREAK,
    "continue":   TokenType.KW_CONTINUE,
    "return":     TokenType.KW_RETURN,
    "import":     TokenType.KW_IMPORT,
    "fn":         TokenType.KW_FN,
    "enum":       TokenType.KW_ENUM,
    "namespace":  TokenType.KW_NAMESPACE,
    "using":      TokenType.KW_USING,
    "const":      TokenType.KW_CONST,
    "private":    TokenType.KW_PRIVATE,
    "protected":  TokenType.KW_PROTECTED,
    "public":     TokenType.KW_PUBLIC,
    "modifier":   TokenType.KW_MODIFIER,
    "try":        TokenType.KW_TRY,
    "catch":      TokenType.KW_CATCH,
    "throw":      TokenType.KW_THROW,
}
