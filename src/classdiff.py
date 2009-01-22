#!/usr/bin/env python2


"""

"""



import sys



IDENTICAL_CLASS = 0
CLASS_DATA_CHANGE = 1 << 1
FIELD_DATA_CHANGE = 1 << 2
METHOD_DATA_CHANGE = 1 << 3
CONST_DATA_CHANGE = 1 << 4



LEFT = "left"
RIGHT = "right"
CHANGE = "change"
SAME = "same"



def WriteFilter(object):
    def __init__(self, threshold, out):
        self.v = threshold
        self.o = out

    def write(self,level,*args):
        if level >= self.v:
            self.o.write(*args)

    def writelines(self,level,*args):
        if level >= self.v:
            self.o.writelines(*args)



def cli_compare_class(options, left, right):
    from javaclass import JavaClassInfo

    if not (isinstance(left, JavaClassInfo) and
            isinstance(right, JavaClassInfo)):
        raise TypeError("wanted JavaClassInfo")

    ret = 0

    # name
    if left.get_this() != right.get_this():
        print "Class name changed: %s to %s" % \
            (left.get_this(), right.get_this())
        ret = CLASS_DATA_CHANGE

    # sourcefile

    # version
    if not options.ignore_version and (left.version != right.version):
        print "Java version changed: %r to %r" % \
            (left.version, right.version)
        ret = CLASS_DATA_CHANGE

    # inheritance
    if left.get_super() != right.get_super():
        print "Superclass changed: %s to %s" % \
            (left.get_super(), right.get_super())

    # interfaces
    li, ri = set(left.get_interfaces()), set(right.get_interfaces())
    if li != ri:
        print "Interfaces changed: (%s) to (%s)" % \
            (", ".join(li), ", ".join(ri))
        ret = CLASS_DATA_CHANGE

    # access flags
    if left.access_flags != right.access_flags:
        print "Access flags changed: %s to %s" % \
            (left.pretty_access_flags(), right.pretty_access_flags())
        ret = CLASS_DATA_CHANGE

    # deprecation
    if not options.ignore_deprecated and \
            (left.is_deprecated() != right.is_deprecated()):
        print "Deprecation became %s" % right.is_deprecated()
        ret = CLASS_DATA_CHANGE

    return ret



def cli_compare_field(options, left, right):
    # if we're here, we already presume name is the same
    
    # type descriptor
    # access flags
    # const val
    
    return 0



def cli_compare_fields(options, left, right):
    # added fields
    # removed fields
    # modified fields
    
    return 0



def cli_compare_code(options, left, right):

    from javaclass import JavaCodeInfo

    if not (isinstance(left, JavaCodeInfo) and
            isinstance(right, JavaCodeInfo)):
        raise TypeError("wanted JavaCodeInfo")

    if (not options.ignore_lines and
        left.get_linenumbertable() != right.get_linenumbertable()):
        return 1

    if left == right:
        return 0
    else:
        return 1



def cli_compare_method(options, left, right):
    
    """ returns zero for same, non-zero for differ """

    from javaclass import JavaMemberInfo

    if not (isinstance(left, JavaMemberInfo) and
            isinstance(right, JavaMemberInfo)):
        raise TypeError("wanted JavaMemberInfo")

    # name and descriptor
    if not (left.get_name() == right.get_name() and
            left.get_descriptor() == right.get_descriptor()):
        return 1

    # access flags
    if left.access_flags != right.access_flags:
        return 1

    # exceptions
    if set(left.get_exceptions()) != set(right.get_exceptions()):
        return 1

    # code
    return cli_compare_code(options, left.get_code(), right.get_code())



def _method_key(meth):
    return meth.get_name()+meth.get_descriptor()



def cli_methods_diff(options, left, right):
    
    """ generator yielding (EVENT, (left_meth, right_meth)) """

    li = {}
    for meth in left.methods:
        li[_method_key(meth)] = meth

    for meth in right.methods:
        key = _method_key(meth)
        lmeth = li.get(key, None)

        if lmeth:
            del li[key]
            if cli_compare_method(options, lmeth, meth):
                yield (CHANGE, (lmeth, meth))
            else:
                yield (SAME, (lmeth, meth))

        else:
            yield (RIGHT, (None, meth))
    
    for meth in li.values():
        yield (LEFT, (meth, None))
        


def cli_collect_methods_diff(options, left, right,
                             added=None, removed=None,
                             changed=None, same=None):

    for event, data in cli_methods_diff(options, left, right):
        if removed is not None and event is LEFT:
            removed.append(data)
        elif added is not None and event is RIGHT:
            added.append(data)
        elif changed is not None and event is CHANGE:
            changed.append(data)
        elif same is not None and event is SAME:
            same.append(data)

    return added, removed, changed, same



def cli_compare_methods(options, left, right):
    
    added, removed, changed = [], [], []
    cli_collect_methods_diff(options, left, right, added, removed, changed)

    ret = 0

    if not options.ignore_added and added:
        print "Added methods:"
        for l,r in added:
            print "  ", r.pretty_name()
        ret = METHOD_DATA_CHANGE

    if removed:
        print "Removed methods:"
        for l,r in removed:
            print "  ", l.pretty_name()
        ret = METHOD_DATA_CHANGE

    if changed:
        print "Changed methods:"
        for l,r in changed:
            print "  ", r.pretty_name()
        ret = METHOD_DATA_CHANGE

    return ret



def cli_compare_constants(options, left, right):

    if options.ignore_pool or left.consts == right.consts:
        return 0

    else:
        print "Constant pool is altered."
        return 1



def options_magic(options):

    # turn a --ignore list into the individual ignore flags
    ign = (i.strip() for i in options.ignore.split(","))
    for i in (i for i in ign if i):
        setattr(options, "ignore_"+i, True)
    


def cli(options, rest):
    import javaclass

    #output_filter = WriteFilter(options.verbosity, sys.stdout)

    options_magic(options)

    left_f, right_f = rest[1:3]
    left_i = javaclass.unpack_classfile(left_f)
    right_i = javaclass.unpack_classfile(right_f)

    ret = 0
    ret += cli_compare_class(options, left_i, right_i)
    ret += cli_compare_fields(options, left_i, right_i)
    ret += cli_compare_methods(options, left_i, right_i)
    ret += cli_compare_constants(options, left_i, right_i)
    
    return ret
    


def create_optparser():
    from optparse import OptionParser

    parse = OptionParser()

    parse.add_option("--verbosity", action="store", type="int")
    #parse.add_option("-v", dest="verbosity", action="increment")

    parse.add_option("--ignore", action="store", default="")
    parse.add_option("--ignore-version", action="store_true")
    parse.add_option("--ignore-lines", action="store_true")
    parse.add_option("--ignore-deprecated", action="store_true")
    parse.add_option("--ignore-added", action="store_true")
    parse.add_option("--ignore-pool", action="store_true")

    return parse
    


def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
