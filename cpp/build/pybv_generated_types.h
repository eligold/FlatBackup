
struct pybv_bv_ViewBuilder_t
{
    PyObject_HEAD
    Ptr<bv::ViewBuilder> v;
};

static PyTypeObject pybv_bv_ViewBuilder_Type =
{
    CV_PYTHON_TYPE_HEAD_INIT()
    MODULESTR".bv_ViewBuilder",
    sizeof(pybv_bv_ViewBuilder_t),
};

static void pybv_bv_ViewBuilder_dealloc(PyObject* self)
{
    ((pybv_bv_ViewBuilder_t*)self)->v.release();
    PyObject_Del(self);
}

template<> PyObject* pybv_from(const Ptr<bv::ViewBuilder>& r)
{
    pybv_bv_ViewBuilder_t *m = PyObject_NEW(pybv_bv_ViewBuilder_t, &pybv_bv_ViewBuilder_Type);
    new (&(m->v)) Ptr<bv::ViewBuilder>(); // init Ptr with placement new
    m->v = r;
    return (PyObject*)m;
}

template<> bool pybv_to(PyObject* src, Ptr<bv::ViewBuilder>& dst, const char* name)
{
    if( src == NULL || src == Py_None )
        return true;
    if(!PyObject_TypeCheck(src, &pybv_bv_ViewBuilder_Type))
    {
        failmsg("Expected bv::ViewBuilder for argument '%s'", name);
        return false;
    }
    dst = ((pybv_bv_ViewBuilder_t*)src)->v.dynamicCast<bv::ViewBuilder>();
    return true;
}


static PyObject* pybv_bv_ViewBuilder_repr(PyObject* self)
{
    char str[1000];
    sprintf(str, "<bv_ViewBuilder %p>", self);
    return PyString_FromString(str);
}



static PyGetSetDef pybv_bv_ViewBuilder_getseters[] =
{
    {NULL}  /* Sentinel */
};

static int pybv_bv_bv_ViewBuilder_ViewBuilder(pybv_bv_ViewBuilder_t* self, PyObject* args, PyObject* kw)
{
    using namespace bv;


    if(PyObject_Size(args) == 0 && (kw == NULL || PyObject_Size(kw) == 0))
    {
        new (&(self->v)) Ptr<bv::ViewBuilder>(); // init Ptr with placement new
        if(self) ERRWRAP2(self->v.reset(new bv::ViewBuilder()));
        return 0;
    }

    return -1;
}

static PyObject* pybv_bv_bv_ViewBuilder_build(PyObject* self, PyObject* args, PyObject* kw)
{
    using namespace bv;

    bv::ViewBuilder* _self_ = NULL;
    if(PyObject_TypeCheck(self, &pybv_bv_ViewBuilder_Type))
        _self_ = ((pybv_bv_ViewBuilder_t*)self)->v.get();
    if (_self_ == NULL)
        return failmsgp("Incorrect type of self (must be 'bv_ViewBuilder' or its derivative)");
    {
    PyObject* pyobj_image = NULL;
    Mat image;
    PyObject* pyobj_imview = NULL;
    Mat imview;

    const char* keywords[] = { "image", "imview", NULL };
    if( PyArg_ParseTupleAndKeywords(args, kw, "O|O:bv_ViewBuilder.build", (char**)keywords, &pyobj_image, &pyobj_imview) &&
        pybv_to(pyobj_image, image, ArgInfo("image", 0)) &&
        pybv_to(pyobj_imview, imview, ArgInfo("imview", 1)) )
    {
        ERRWRAP2(_self_->build(image, imview));
        return pybv_from(imview);
    }
    }
    PyErr_Clear();

    {
    PyObject* pyobj_image = NULL;
    UMat image;
    PyObject* pyobj_imview = NULL;
    UMat imview;

    const char* keywords[] = { "image", "imview", NULL };
    if( PyArg_ParseTupleAndKeywords(args, kw, "O|O:bv_ViewBuilder.build", (char**)keywords, &pyobj_image, &pyobj_imview) &&
        pybv_to(pyobj_image, image, ArgInfo("image", 0)) &&
        pybv_to(pyobj_imview, imview, ArgInfo("imview", 1)) )
    {
        ERRWRAP2(_self_->build(image, imview));
        return pybv_from(imview);
    }
    }

    return NULL;
}



static PyMethodDef pybv_bv_ViewBuilder_methods[] =
{
    {"build", (PyCFunction)pybv_bv_bv_ViewBuilder_build, METH_VARARGS | METH_KEYWORDS, "build(image[, imview]) -> imview\n."},

    {NULL,          NULL}
};

static void pybv_bv_ViewBuilder_specials(void)
{
    pybv_bv_ViewBuilder_Type.tp_base = NULL;
    pybv_bv_ViewBuilder_Type.tp_dealloc = pybv_bv_ViewBuilder_dealloc;
    pybv_bv_ViewBuilder_Type.tp_repr = pybv_bv_ViewBuilder_repr;
    pybv_bv_ViewBuilder_Type.tp_getset = pybv_bv_ViewBuilder_getseters;
    pybv_bv_ViewBuilder_Type.tp_init = (initproc)pybv_bv_bv_ViewBuilder_ViewBuilder;
    pybv_bv_ViewBuilder_Type.tp_methods = pybv_bv_ViewBuilder_methods;
}
