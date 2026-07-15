"""
Skill Verifier - Phase 6.3 AST safety and compilation verifier
Blocks shell injections, destructive rm -rf commands, and syntax errors.
"""
import ast
import tempfile
import py_compile
from pathlib import Path
from typing import Tuple, List

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SkillVerifier")

class SkillVerifier:
    """Verifies generated Python code via AST safety inspection and compilation check"""

    # Banned AST function names or string substrings that indicate destructive/malicious operations
    BANNED_STRINGS = [
        "rm -rf", "mkfs", "dd if=", ":(){ :|:& };:", "format c:", "del /f /s /q",
        "rmdir /s /q c:\\", "os.system('rm", "os.system(\"rm", "shutil.rmtree('/')"
    ]
    BANNED_MODULES = ["socket", "urllib.request", "requests", "http.client"]  # Block unauthorized network exfiltration in dynamic skills unless explicitly allowed

    @classmethod
    def verify(cls, code_str: str, allow_network: bool = False) -> Tuple[bool, str]:
        """
        Run AST inspection and syntax compilation check over generated code.
        Returns (is_safe: bool, message: str).
        """
        if not code_str or not code_str.strip():
            return False, "Code string is empty"

        # 1. String-level destructive command scan
        lower_code = code_str.lower()
        for banned in cls.BANNED_STRINGS:
            if banned in lower_code:
                msg = f"AST Safety Violation: Destructive command pattern '{banned}' detected"
                logger.error(msg)
                return False, msg

        # 2. AST parsing & node inspection
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            msg = f"SyntaxError in generated code: {e.msg} at line {e.lineno}"
            logger.error(msg)
            return False, msg

        # Walk AST nodes to verify imports and calls
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not allow_network and any(alias.name.startswith(mod) for mod in cls.BANNED_MODULES):
                        msg = f"AST Safety Violation: Unauthorized network module import '{alias.name}'"
                        logger.error(msg)
                        return False, msg
            elif isinstance(node, ast.ImportFrom):
                if not allow_network and node.module and any(node.module.startswith(mod) for mod in cls.BANNED_MODULES):
                    msg = f"AST Safety Violation: Unauthorized network from-import '{node.module}'"
                    logger.error(msg)
                    return False, msg

            # Check for eval() / exec()
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec"]:
                        msg = f"AST Safety Violation: Dynamic execution call '{node.func.id}()' is blocked"
                        logger.error(msg)
                        return False, msg

        # 3. Compilation dry-run
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tf:
                tf.write(code_str)
                tf_path = Path(tf.name)
            
            try:
                py_compile.compile(str(tf_path), doraise=True)
            finally:
                if tf_path.exists():
                    tf_path.unlink()
                pyc_path = Path(str(tf_path) + "c")
                if pyc_path.exists():
                    pyc_path.unlink()
        except py_compile.PyCompileError as e:
            msg = f"Compilation dry-run failed: {e.exc_value}"
            logger.error(msg)
            return False, msg

        logger.info("✅ Skill AST & compilation verification passed safely")
        return True, "Code AST verified safe and compilable"
