PYTHON := python
LST2HDF5 := lst2hdf5
HIST_FROM_MPA := hist_from_mpa
USEFUL_FILES := useful_files
EXTRACT_ROI := extract_roi
GENERATE_REPORT_SHEET := generate_report_sheet

LST_DIR := /run/media/hpahl/HannesExtHDD/Fe_DR_TimeResolvedJuly2020
RUN_FILE := $(LST_DIR)/runs.csv
LST_FILES := $(patsubst %,$(LST_DIR)/%,$(shell $(PYTHON) -m $(USEFUL_FILES) $(RUN_FILE)))#$(wildcard $(LST_DIR)/*.lst)
HDF_TRGTS := $(subst lst,h5,$(LST_FILES))

HIST_ADC1 := $(subst .lst,_ADC1.pdf,$(LST_FILES))
HIST_ADC2 := $(subst .lst,_ADC2.pdf,$(LST_FILES))
HIST_ADC3 := $(subst .lst,_ADC3.pdf,$(LST_FILES))
HIST_ADC2_ADC1 := $(subst .lst,_ADC2_ADC1.pdf,$(LST_FILES))
HIST_ADC2_ADC3_DR1 := $(subst .lst,_ADC2_ADC3_DR1.pdf,$(LST_FILES))
HIST_ADC2_ADC3_DR2 := $(subst .lst,_ADC2_ADC3_DR2.pdf,$(LST_FILES))
HIST_ADC2_ADC1_DR2 := $(subst .lst,_ADC2_ADC1_DR2.pdf,$(LST_FILES))
HISTS := $(HIST_ADC1) $(HIST_ADC2) $(HIST_ADC3) $(HIST_ADC2_ADC1) $(HIST_ADC2_ADC3_DR1) $(HIST_ADC2_ADC3_DR2) $(HIST_ADC2_ADC1_DR2)

ROI_DR1 := $(subst .lst,_DR1.h5roi,$(LST_FILES))
ROI_DR2 := $(subst .lst,_DR2.h5roi,$(LST_FILES))
ROIS := $(ROI_DR1) $(ROI_DR2)

REPORT_SHEETS_MD :=$(subst lst,md,$(LST_FILES))
REPORT_SHEETS_PDF :=$(subst lst,pdf,$(LST_FILES))
MAIN_REPORT_MD := $(LST_DIR)/main_report.md
MAIN_REPORT_PDF := $(LST_DIR)/main_report.pdf
REPORTS := $(REPORT_SHEETS_MD) $(MAIN_REPORT_MD) $(MAIN_REPORT_PDF)


.PHONY : h5files histograms rois reports clean all cleanreports

all : h5files rois histograms reports
h5files : $(HDF_TRGTS)
rois : $(ROIS)
histograms : $(HISTS)
reports: $(REPORTS)

cleanreports:
	rm $(REPORTS)
# clean : cleanplots
# 	rm mendeley_filtered.bib

%.h5 : %.lst
	$(PYTHON) -m $(LST2HDF5) $< --out $@ --yes

%_DR1.h5roi : %.h5
	$(PYTHON) -m $(EXTRACT_ROI) $< ADC1 --strip 5500 7500 --out $@ --yes

%_DR2.h5roi : %.h5
	$(PYTHON) -m $(EXTRACT_ROI) $< ADC2 --ychannel ADC1 --poly 1 5000 8191 5790 8191 8191 1 8191 --out $@ --yes

%_ADC1.pdf : %.h5
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC1 --pdf --png --out $@ --yes

%_ADC2.pdf : %.h5
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --pdf --png --out $@ --yes

%_ADC3.pdf : %.h5
	# some early files don't have ADC3 -> leading dash forces 'make' to press on despite error
	-$(PYTHON) -m $(HIST_FROM_MPA) $< ADC3 --pdf --png --out $@ --yes

%_ADC2_ADC1.pdf : %.h5
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --ychannel ADC1 --pdf --png --out $@ --yes

%_ADC2_ADC3_DR1.pdf : %_DR1.h5roi
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --ychannel ADC3 --pdf --png --out $@ --yes

%_ADC2_ADC3_DR2.pdf : %_DR2.h5roi
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --ychannel ADC3 --pdf --png --out $@ --yes

%_ADC2_ADC1_DR2.pdf : %_DR2.h5roi
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --ychannel ADC1 --pdf --png --out $@ --yes

$(REPORT_SHEETS_MD) : %.md : $(GENERATE_REPORT_SHEET).py#%_ADC1.pdf %_ADC2.pdf %_ADC3.pdf %_ADC2_ADC1.pdf %_ADC2_ADC3_DR1.pdf
	$(PYTHON) -m $(GENERATE_REPORT_SHEET) $@ --out $@ --yes

# $(REPORT_SHEETS_PDF) : %.pdf : %.md
# 	pandoc $< -t latex -o $@

$(MAIN_REPORT_MD) : $(REPORT_SHEETS_MD)
	cat $^ > $@

$(MAIN_REPORT_PDF) : $(MAIN_REPORT_MD) $(HISTS)
	cp pream.latex $(LST_DIR)
	cd $(LST_DIR) \
	&& pandoc -t latex -s --template=pream.latex  main_report.md \
	| sed -e 's/\\includegraphics/&[height=.4\\textheight]/' -e 's/.png/.pdf/' > main_report.tex \
	&& latexmk -pdf main_report.tex \
	&& cd -