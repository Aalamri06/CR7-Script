import tkinter as tk
from tkinter import scrolledtext, messagebox
import re
import sys

# -----------------------------
# ⚽ CR7 SCRIPT LEXER
# -----------------------------
KEYWORDS = {
    "FUNCTION": ["play", "kickoff", "whistle"],
    "TYPE": ["goal", "player", "flag", "match"],
    "CONTROL": ["referee", "bench", "practice", "drill"],
    "OUTPUT": ["announce"],
    "INPUT": ["listen"],
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


# -----------------------------
# ⚙️ PARSER
# -----------------------------
class CR7Parser:
    def __init__(self, tokens, output_box=None):
        self.tokens = tokens
        self.pos = 0
        self.output_box = output_box  # GUI output reference

    def log(self, msg, color=None):
        """Helper to print or send output to GUI with color"""
        if self.output_box:
            self.output_box.configure(state="normal")
            if color:
                self.output_box.insert(tk.END, msg + "\n", color)
            else:
                self.output_box.insert(tk.END, msg + "\n")
            self.output_box.configure(state="disabled")
            self.output_box.see(tk.END)
        else:
            print(msg)

    def current_token(self):
        return self.tokens[self.pos]

    def lookahead(self, n=1):
        """Safely look ahead to next token"""
        if self.pos + n < len(self.tokens):
            return self.tokens[self.pos + n]
        return ("EOF", "")

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
        self.log(f"[Syntax Error] {msg} at token '{actual_value}' (type {actual_kind})", "error")
        raise SystemExit(1)

    # ----------------------------
    # PROGRAM ENTRY
    # ----------------------------
    def parse_program(self):
        self.log("[Parser] Starting CR7 Script Parsing...\n", "header")

        while self.current_token()[0] != "EOF":
            kind, value = self.current_token()
            if kind == "META_KEYWORD":
                self.parse_meta()
            elif kind == "FUNCTION_KEYWORD":
                self.parse_function()
            else:
                self.error(f"Unexpected statement start: {value}")

        self.log("\n[Parser] Parsing completed successfully ✅", "success")
        messagebox.showinfo("Parsing Success", "CR7 Script parsed successfully ✅")

    # ----------------------------
    # META (#import stadium)
    # ----------------------------
    def parse_meta(self):
        self.match("META_KEYWORD", "#import")
        if self.current_token()[1] == "stadium":
            self.match("META_KEYWORD", "stadium")
        else:
            self.error("Expected 'stadium' after #import")
        self.log("→ Meta statement parsed (#import stadium)", "info")

    # ----------------------------
    # FUNCTION
    # ----------------------------
    def parse_function(self):
        self.match("FUNCTION_KEYWORD", "play")

        # Function name can be ID or FUNCTION_KEYWORD (e.g., kickoff)
        kind, value = self.current_token()
        if kind in ("ID", "FUNCTION_KEYWORD"):
            self.pos += 1
        else:
            self.error("Expected function name after 'play'")

        self.match("LPAREN")
        self.parse_param_list()
        self.match("RPAREN")
        self.match("LBRACE")
        self.parse_statement_list()
        self.match("RBRACE")
        self.log("→ Function parsed", "info")

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
        self.log("→ Declaration parsed", "info")

    def parse_assignment(self):
        self.match("ID")
        self.match("ASSIGN")
        self.parse_expr()
        self.match("END")
        self.log("→ Assignment parsed", "info")

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
        self.log("→ If statement parsed", "info")

    def parse_while(self):
        self.match("CONTROL_KEYWORD", "practice")
        self.match("LPAREN")
        self.parse_condition()
        self.match("RPAREN")
        self.match("LBRACE")
        self.parse_statement_list()
        self.match("RBRACE")
        self.log("→ While parsed", "info")

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
        self.log("→ For parsed", "info")

    def parse_declaration_in_for(self):
        self.match("TYPE_KEYWORD")
        self.match("ID")
        if self.current_token()[0] == "ASSIGN":
            self.match("ASSIGN")
            self.parse_expr()
        self.log("→ For-init declaration parsed", "info")

    def parse_assignment_in_for(self):
        self.match("ID")
        kind, value = self.current_token()
        if kind == "ASSIGN":
            self.match("ASSIGN")
            self.parse_expr()
            self.log("→ For-update parsed (assignment)", "info")
        elif kind == "OP" and value in ("++", "--"):
            self.match("OP")
            self.log("→ For-update parsed (increment/decrement)", "info")
        else:
            self.error("Expected '=' or '++'/'--' in for update")

    def parse_output(self):
        self.match("OUTPUT_KEYWORD")
        self.parse_expr()
        self.match("END")
        self.log("→ Output parsed", "info")

    def parse_input(self):
        self.match("INPUT_KEYWORD")
        self.match("ID")
        self.match("END")
        self.log("→ Input parsed", "info")

    def parse_return(self):
        self.match("FUNCTION_KEYWORD", "whistle")
        self.parse_expr()
        self.match("END")
        self.log("→ Return parsed", "info")

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

        # Identifier or function call (ID or FUNCTION_KEYWORD)
        if kind in ("ID", "FUNCTION_KEYWORD"):
            next_kind, _ = self.lookahead(1)
            if next_kind == "LPAREN":
                ident = self.match(kind)
                self.match("LPAREN")
                if self.current_token()[0] != "RPAREN":
                    self.parse_expr()
                    while self.current_token()[0] == "COMMA":
                        self.match("COMMA")
                        self.parse_expr()
                self.match("RPAREN")
                self.log(f"→ Function call parsed ({ident})", "info")
            else:
                self.match(kind)

        elif kind in ("NUMBER", "STRING"):
            self.match(kind)

        elif kind == "LPAREN":
            self.match("LPAREN")
            self.parse_expr()
            self.match("RPAREN")

        else:
            self.error("Invalid factor")


# -----------------------------
# ⚽ GUI IMPLEMENTATION
# -----------------------------
def run_compiler():
    code = input_box.get("1.0", tk.END).strip()
    token_output.configure(state="normal")
    parser_output.configure(state="normal")
    token_output.delete("1.0", tk.END)
    parser_output.delete("1.0", tk.END)

    if not code:
        messagebox.showwarning("Empty Code", "Please enter CR7 Script code to compile.")
        return

    # Tokenization
    try:
        tokens = tokenize(code)
        token_output.insert(tk.END, "[CR7 Compiler] Tokens Generated:\n\n", "header")
        for kind, value in tokens:
            token_output.insert(tk.END, f"{kind:18} → {value}\n")
    except RuntimeError as e:
        token_output.insert(tk.END, f"[Lexer Error] {e}\n", "error")
        return

    # Parsing
    try:
        parser = CR7Parser(tokens, parser_output)
        parser.parse_program()
    except SystemExit:
        pass


# GUI SETUP
root = tk.Tk()
root.title("⚽ CR7 Script Compiler (Lexer + Parser)")
root.geometry("1050x750")
root.configure(bg="#222831")

title = tk.Label(root, text="⚽ CR7 Script Compiler (Lexer + Parser)", font=("Arial", 18, "bold"), fg="#FFD369", bg="#222831")
title.pack(pady=10)

input_label = tk.Label(root, text="Write your CR7 Script code below:", font=("Arial", 12, "bold"), fg="#EEEEEE", bg="#222831")
input_label.pack()

input_box = scrolledtext.ScrolledText(root, width=115, height=12, font=("Consolas", 11), bg="#393E46", fg="#EEEEEE", insertbackground="white")
input_box.pack(padx=15, pady=10)

run_button = tk.Button(root, text="Run 🏁", command=run_compiler, font=("Arial", 14, "bold"), bg="#FFD369", fg="#222831", padx=20, pady=5)
run_button.pack(pady=10)

token_label = tk.Label(root, text="Token Output:", font=("Arial", 12, "bold"), fg="#EEEEEE", bg="#222831")
token_label.pack()
token_output = scrolledtext.ScrolledText(root, width=115, height=10, font=("Consolas", 10), bg="#393E46", fg="#EEEEEE", insertbackground="white")
token_output.pack(padx=15, pady=10)

parser_label = tk.Label(root, text="Parser Output:", font=("Arial", 12, "bold"), fg="#EEEEEE", bg="#222831")
parser_label.pack()
parser_output = scrolledtext.ScrolledText(root, width=115, height=10, font=("Consolas", 10), bg="#393E46", fg="#EEEEEE", insertbackground="white")
parser_output.pack(padx=15, pady=10)

# Add color tags
for box in [token_output, parser_output]:
    box.tag_config("error", foreground="#FF5C5C")
    box.tag_config("success", foreground="#00FF7F")
    box.tag_config("header", foreground="#FFD369", font=("Consolas", 10, "bold"))
    box.tag_config("info", foreground="#00BFFF")

root.mainloop()
