.PHONY: verify paper clean

verify:
	./verify_all.sh

paper:
	cd paper && pdflatex -interaction=nonstopmode -halt-on-error article.tex
	cd paper && pdflatex -interaction=nonstopmode -halt-on-error article.tex

clean:
	cd paper && rm -f article.aux article.log article.out
