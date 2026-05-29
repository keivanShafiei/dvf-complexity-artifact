.PHONY: all clean certify paper

all:
	snakemake --use-conda --cores all --configfile=experiments/configs/paper_final.yaml

paper: all
	cd paper && latexmk -pdf -interaction=nonstopmode main.tex

clean:
	rm -rf experiments/data experiments/figures figures/ tables/
	snakemake --delete-all-output

certify:
	@bash artifact/evaluation/certify.sh
