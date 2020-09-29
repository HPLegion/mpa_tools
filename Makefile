# This makefile currently ignores the state of the meta files, cause make's string handling is too dumb for an easy fix

empty :=
space := $(empty) $(empty)
PYTHON := python
LST2HDF5 := lst2hdf5
GENERATE_META_DATA := generate_meta_data
GENERATE_HIST := generate_hist
PLOT_HIST := plot_hist
USEFUL_FILES := useful_files
EXTRACT_ROI := extract_roi
GENERATE_REPORT_SHEET := generate_report_sheet
FIT_TIME_RESOLVED_SPECTRUM := fit_time_resolved_spectrum

LST_DIR := /run/media/hpahl/HannesExSSD/Fe_DR_TimeResolvedJuly2020
RUN_FILE := $(LST_DIR)/runs.csv
LST_FILES := $(patsubst %,$(LST_DIR)/%,$(shell $(PYTHON) -m $(USEFUL_FILES) $(RUN_FILE)))#$(wildcard $(LST_DIR)/*.lst)
HDF_TRGTS := $(LST_FILES:lst=h5)
META_TRGTS := $(LST_FILES:lst=meta)

ROI_DR1 := $(LST_FILES:.lst=_DR1.h5roi)
ROI_DR2 := $(LST_FILES:.lst=_DR2.h5roi)
ROIS := $(ROI_DR1) $(ROI_DR2)

HIST_ADC1 := $(LST_FILES:.lst=_ADC1.h5hist)
HIST_ADC2 := $(LST_FILES:.lst=_ADC2.h5hist)
HIST_ADC3 := $(LST_FILES:.lst=_ADC3.h5hist)
HIST_ADC2_ADC1 := $(LST_FILES:.lst=_ADC2_ADC1.h5hist)
HIST_DR1_ADC2_ADC3 := $(LST_FILES:.lst=_DR1_ADC2_ADC3.h5hist)
HIST_DR2_ADC2_ADC3 := $(LST_FILES:.lst=_DR2_ADC2_ADC3.h5hist)
HIST_DR2_ADC2_ADC1 := $(LST_FILES:.lst=_DR2_ADC2_ADC1.h5hist)
HISTS := $(HIST_ADC1) $(HIST_ADC2) $(HIST_ADC3) $(HIST_ADC2_ADC1) $(HIST_DR1_ADC2_ADC3) $(HIST_DR2_ADC2_ADC3) $(HIST_DR2_ADC2_ADC1)

FIT_DR2_ADC2_ADC3 := $(HIST_DR2_ADC2_ADC3:h5hist=h5fit)
FITS = $(FIT_DR2_ADC2_ADC3)

PLOT_HISTS := $(HISTS:.h5hist=.pdf)
PLOT_FITS := $(FITS:.h5fit=.pdf)
PLOTS := $(PLOT_HISTS) $(PLOT_FITS)

REPORT_SHEETS_MD :=$(LST_FILES:lst=md)
REPORT_SHEETS_PDF :=$(LST_FILES:lst=pdf)
MAIN_REPORT_MD := $(LST_DIR)/main_report.md
MAIN_REPORT_PDF := $(LST_DIR)/main_report.pdf
REPORTS := $(REPORT_SHEETS_MD) $(MAIN_REPORT_MD) $(MAIN_REPORT_PDF)


.PHONY : h5files meta histograms rois reports clean all cleanreports cleanmeta fits

all : h5files meta rois histograms plots reports
h5files : $(HDF_TRGTS)
meta : $(META_TRGTS)
rois : $(ROIS)
histograms : $(HISTS)
reports: $(REPORTS)
plots: $(PLOTS)
fits: $(FITS)

cleanreports:
	rm $(REPORTS)

cleanmeta:
	rm $(META_TRGTS)

cleanplots:
	rm $(PLOTS) $(PLOTS:pdf=png)


%.h5 : %.lst
	$(PYTHON) -m $(LST2HDF5) $< --out $@ --yes

%.meta : $(RUN_FILE)
	$(PYTHON) -m $(GENERATE_META_DATA) $(RUN_FILE) $(notdir $*).lst --out $@ --yes

$(PLOT_HISTS) : %.pdf : %.h5hist
	$(PYTHON) -m $(PLOT_HIST) $< --out $@ --yes --pdf --png
# --meta $(dir $*)$(subst $(space),_,$(wordlist 1,3,$(subst _, ,$(notdir $*)))).meta

$(FIT_DR2_ADC2_ADC3) : %.h5fit : %.h5hist
	$(PYTHON) -m $(FIT_TIME_RESOLVED_SPECTRUM) $< --out $@ --yes

%_DR1.h5roi : %.h5
	$(PYTHON) -m $(EXTRACT_ROI) $< ADC1 --strip 5500 7500 --out $@ --yes

%_DR2.h5roi : %.h5
	$(PYTHON) -m $(EXTRACT_ROI) $< ADC2 --ychannel ADC1 --poly 1 5000 8191 5790 8191 8191 1 8191 --out $@ --yes

%_ADC1.h5hist : %.h5
	$(PYTHON) -m $(GENERATE_HIST) $< ADC1 --out $@ --yes

%_ADC2.h5hist : %.h5
	$(PYTHON) -m $(GENERATE_HIST) $< ADC2 --out $@ --yes

%_ADC3.h5hist : %.h5
	# some early files don't have ADC3 -> leading dash forces 'make' to press on despite error
	-$(PYTHON) -m $(GENERATE_HIST) $< ADC3 --out $@ --yes

%_ADC2_ADC1.h5hist : %.h5
	$(PYTHON) -m $(GENERATE_HIST) $< ADC2 --ychannel ADC1 --out $@ --yes

%_DR1_ADC2_ADC3.h5hist : %_DR1.h5roi
	$(PYTHON) -m $(GENERATE_HIST) $< ADC2 --ychannel ADC3 --out $@ --yes

%_DR2_ADC2_ADC3.h5hist : %_DR2.h5roi
	$(PYTHON) -m $(GENERATE_HIST) $< ADC2 --ychannel ADC3 --out $@ --yes

%_DR2_ADC2_ADC1.h5hist : %_DR2.h5roi
	$(PYTHON) -m $(GENERATE_HIST) $< ADC2 --ychannel ADC1 --out $@ --yes

$(REPORT_SHEETS_MD) : %.md : %.meta $(GENERATE_REPORT_SHEET).py
	$(PYTHON) -m $(GENERATE_REPORT_SHEET) $@ --out $@ --yes --meta $<

# $(REPORT_SHEETS_PDF) : %.pdf : %.md
# 	pandoc $< -t latex -o $@

$(MAIN_REPORT_MD) : $(REPORT_SHEETS_MD)
	cat $^ > $@

$(MAIN_REPORT_PDF) : $(MAIN_REPORT_MD) $(PLOTS)
	cp pream.latex $(LST_DIR)
	cd $(LST_DIR) \
	&& pandoc -t latex -s --template=pream.latex  main_report.md \
	| sed -e 's/\\includegraphics/&[height=.4\\textheight]/' -e 's/.png/.pdf/' > main_report.tex \
	&& latexmk -pdf main_report.tex \
	&& cd -