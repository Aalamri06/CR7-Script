import re
import sys
import os

KEYWORDS = {
    "FUNCTION": ["play", "kickoff", "whistle"],
    "TYPE": ["goal", "player", "flag", "match"],
    "CONTROL": ["referee", "bench", "practice", "drill"],
    "INPUT": ["listen"],
    "OUTPUT": ["announce"],
    "META": ["#import", "stadium"]
}

token_specification = [
    ("META",     r"#\w+"),
    ("COMMENT",  r"//.*"),
    ("NUMBER",   r"\d+(\.\d+)?"),
    ("ASSIGN",   r"="),
    ("COMMA",    r","),
    ("END",      r";"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("STRING",   r'"[^"]*"'),
    ("ID",       r"[A-Za-z_]\w*"),
    ("OP",       r"[+\-*/<>!=]+"),
    ("NEWLINE",  r"\n"),
    ("SKIP",     r"[ \t]+"),
    ("MISMATCH", r"."),
]

token_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in token_specification)

# ----------------------------
# LEXER
# ----------------------------
def tokenize(code):
    tokens = []
    for match in re.finditer(token_regex, code):
        kind = match.lastgroup
        value = match.group()

        if kind == "COMMENT":
            continue
        elif kind == "META":
            tokens.append(("META_KEYWORD", value))
            continue
        elif kind == "ID":
            for group_name, words in KEYWORDS.items():
                if value in words:
                    kind = f"{group_name}_KEYWORD"
                    break
        elif kind in ("SKIP", "NEWLINE"):
            continue
        elif kind == "MISMATCH":
            raise RuntimeError(f"Unexpected token: {value}")
        tokens.append((kind, value))
    tokens.append(("EOF", ""))
    return tokens

# ----------------------------
# PARSER
# ----------------------------
class CR7Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        return self.tokens[self.pos]

    def match(self, expected_type, expected_value=None):
        kind, value = self.current_token()
        if kind == expected_type and (expected_value is None or value == expected_value):
            self.pos += 1
            return value
        else:
            self.error(f"Expected {expected_type}" + (f"('{expected_value}')" if expected_value else ""), kind, value)

    def error(self, msg, actual_kind=None, actual_value=None):
        if actual_kind is None or actual_value is None:
            actual_kind, actual_value = self.current_token()
        print(f"[Syntax Error] {msg} at token '{actual_value}' (type {actual_kind})")
        sys.exit(1)

    # ----------------------------
    # PROGRAM ENTRY
    # ----------------------------
    def parse_program(self):
        print("[Parser] Starting CR7 Script Parsing...\n")

        while self.current_token()[0] != "EOF":
            kind, value = self.current_token()
            if kind == "META_KEYWORD":
                self.parse_meta()
            elif kind == "FUNCTION_KEYWORD":
                self.parse_function()
            else:
                self.error(f"Unexpected statement start: {value}")

        print("\n[Parser] Parsing completed successfully ✅")

    # ----------------------------
    # META (#import stadium)
    # ----------------------------
    def parse_meta(self):
        self.match("META_KEYWORD", "#import")
        if self.current_token()[1] == "stadium":
            self.match("META_KEYWORD", "stadium")
        else:
            self.error("Expected 'stadium' after #import")
        print("→ Meta statement parsed (#import stadium)")

    # ----------------------------
    # FUNCTION
    # ----------------------------
    def parse_function(self):
        self.match("FUNCTION_KEYWORD", "play")
        self.match("ID")  # function name
        self.match("LPAREN")
        self.parse_param_list()
        self.match("RPAREN")
        self.match("LBRACE")
        self.parse_statement_list()
        self.match("RBRACE")
        print("→ Function parsed")

    def parse_param_list(self):
        if self.current_token()[0] == "TYPE_KEYWORD":
            self.match("TYPE_KEYWORD")
            self.match("ID")
            while self.current_token()[0] == "COMMA":
                self.match("COMMA")
                self.match("TYPE_KEYWORD")
                self.match("ID")

    # ----------------------------
    # STATEMENTS
    # ----------------------------
    def parse_statement_list(self):
        while self.current_token()[0] not in ("EOF", "RBRACE"):
            self.parse_statement()

    def parse_statement(self):
        kind, value = self.current_token()

        if kind == "TYPE_KEYWORD":
            self.parse_declaration()
        elif kind == "ID":
            self.parse_assignment()
        elif kind == "CONTROL_KEYWORD":
            if value == "referee":
                self.parse_if()
            elif value == "practice":
                self.parse_while()
            elif value == "drill":
                self.parse_for()
            elif value == "bench":
                return
            else:
                self.error(f"Unknown control keyword '{value}'", kind, value)
        elif kind == "OUTPUT_KEYWORD":
            self.parse_output()
        elif kind == "INPUT_KEYWORD":
            self.parse_input()
        elif kind == "FUNCTION_KEYWORD" and value == "whistle":
            self.parse_return()
        else:
            self.error(f"Unexpected statement start: {value}", kind, value)

    def parse_declaration(self):
        self.match("TYPE_KEYWORD")
        self.match("ID")
        if self.current_token()[0] == "ASSIGN":
            self.match("ASSIGN")
            self.parse_expr()
        self.match("END")
        print("→ Declaration parsed")

    def parse_assignment(self):
        self.match("ID")
        self.match("ASSIGN")
        self.parse_expr()
        self.match("END")
        print("→ Assignment parsed")

    def parse_if(self):
        self.match("CONTROL_KEYWORD", "referee")
        self.match("LPAREN")
        self.parse_condition()
        self.match("RPAREN")
        self.match("LBRACE")
        self.parse_statement_list()
        self.match("RBRACE")

        if self.current_token()[1] == "bench":
            self.match("CONTROL_KEYWORD", "bench")
            self.match("LBRACE")
            self.parse_statement_list()
            self.match("RBRACE")
        print("→ If statement parsed")

    def parse_while(self):
        self.match("CONTROL_KEYWORD", "practice")
        self.match("LPAREN")
        self.parse_condition()
        self.match("RPAREN")
        self.match("LBRACE")
        self.parse_statement_list()
        self.match("RBRACE")
        print("→ While parsed")

    def parse_for(self):
        self.match("CONTROL_KEYWORD", "drill")
        self.match("LPAREN")
        if self.current_token()[0] == "TYPE_KEYWORD":
            self.parse_declaration_in_for()
        elif self.current_token()[0] == "ID":
            self.parse_assignment_in_for()
        self.match("END")
        if self.current_token()[0] != "END":
            self.parse_condition()
        self.match("END")
        if self.current_token()[0] == "ID":
            self.parse_assignment_in_for()
        self.match("RPAREN")
        self.match("LBRACE")
        self.parse_statement_list()
        self.match("RBRACE")
        print("→ For parsed")

    def parse_declaration_in_for(self):
        self.match("TYPE_KEYWORD")
        self.match("ID")
        if self.current_token()[0] == "ASSIGN":
            self.match("ASSIGN")
            self.parse_expr()
        print("→ For-init declaration parsed")

    def parse_assignment_in_for(self):
        # support i = i + 1 or i++ / i--
        self.match("ID")
        kind, value = self.current_token()
        if kind == "ASSIGN":
            self.match("ASSIGN")
            self.parse_expr()
            print("→ For-update parsed (assignment)")
        elif kind == "OP" and value in ("++", "--"):
            self.match("OP")
            print("→ For-update parsed (increment/decrement)")
        else:
            self.error("Expected '=' or '++'/'--' in for update")


    def parse_output(self):
        self.match("OUTPUT_KEYWORD")
        self.parse_expr()
        self.match("END")
        print("→ Output parsed")

    def parse_input(self):
        self.match("INPUT_KEYWORD")
        self.match("ID")
        self.match("END")
        print("→ Input parsed")

    def parse_return(self):
        self.match("FUNCTION_KEYWORD", "whistle")
        self.parse_expr()
        self.match("END")
        print("→ Return parsed")

    def parse_condition(self):
        self.parse_expr()
        if self.current_token()[0] == "OP":
            self.match("OP")
            self.parse_expr()
        else:
            self.error("Expected relational operator in condition")

    def parse_expr(self):
        self.parse_term()
        while self.current_token()[0] == "OP" and self.current_token()[1] in ("+", "-"):
            self.match("OP")
            self.parse_term()

    def parse_term(self):
        self.parse_factor()
        while self.current_token()[0] == "OP" and self.current_token()[1] in ("*", "/"):
            self.match("OP")
            self.parse_factor()

    def parse_factor(self):
        kind, value = self.current_token()
        if kind in ("NUMBER", "STRING", "ID"):
            self.match(kind)
        elif kind == "LPAREN":
            self.match("LPAREN")
            self.parse_expr()
            self.match("RPAREN")
        else:
            self.error("Invalid factor")

# ----------------------------
# MAIN
# ----------------------------
def main():
    if len(sys.argv) != 2:
        print("Usage: python cr7_compiler.py <filename.cr7>")
        return

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"[CR7 Compiler] File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    try:
        tokens = tokenize(code)
        parser = CR7Parser(tokens)
        parser.parse_program()
    except RuntimeError as e:
        print(f"[Lexer Error] {e}")


if __name__ == "__main__":
    main()
