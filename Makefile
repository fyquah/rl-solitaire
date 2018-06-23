all: rules.exe

rules.exe: rules.mli rules.ml
	ocamlopt.opt -O3 -unbox-closures $^ -o test.exe
