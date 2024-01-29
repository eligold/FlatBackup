static PyMethodDef methods_bv[] = {
    {NULL, NULL}
};

static ConstDef consts_bv[] = {
    {NULL, 0}
};

static void init_submodules(PyObject * root) 
{
  init_submodule(root, MODULESTR"", methods_bv, consts_bv);
};
