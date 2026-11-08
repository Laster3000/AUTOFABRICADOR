"""R057 trusted bool guard only; no historical model needed for unit test."""
import ast,unittest
from autofab import python_general_repair
class BoolExactTypeGuardR057(unittest.TestCase):
    def test_exact_source_is_one_function_and_one_argument(self):
        src=python_general_repair.EXACT_SOURCE
        root=ast.parse(src)
        self.assertEqual(len(root.body),1)
        self.assertIsInstance(root.body[0],ast.FunctionDef)
        self.assertEqual(root.body[0].name,"unique_positive_ints")
        self.assertEqual(len(root.body[0].args.args),1)
        self.assertEqual(src.count("isinstance(item, int)"),1)
    def test_only_type_guard_transform_preserves_rest(self):
        a=python_general_repair.EXACT_SOURCE
        b=a.replace("isinstance(item, int)","type(item) is int")
        ast.parse(b)
        self.assertEqual(b.replace("type(item) is int","isinstance(item, int)"),a)
        self.assertEqual(b.count("type(item) is int"),1)
    def test_type_guard_not_equal_to_int_subclass_for_bool(self):
        self.assertTrue(isinstance(True,int))
        self.assertFalse(type(True) is int)
        self.assertTrue(type(5) is int)
    def test_repair_id_safety(self):
        self.assertTrue(python_general_repair._ID.fullmatch("GR-0123456789abcdef"))
        self.assertFalse(python_general_repair._ID.fullmatch("GR-../../evil"))
