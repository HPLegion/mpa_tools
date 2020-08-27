PYTHON := python
LST2HDF5 := lst2hdf5
HIST_FROM_MPA := hist_from_mpa
USEFUL_FILES := useful_files
GENERATE_ROI := generate_roi

LST_DIR := /run/media/hpahl/HannesExtHDD/Fe_DR_TimeResolvedJuly2020
RUN_FILE := $(LST_DIR)/runs.csv
LST_FILES := $(patsubst %,$(LST_DIR)/%,$(shell $(PYTHON) -m $(USEFUL_FILES) $(RUN_FILE)))#$(wildcard $(LST_DIR)/*.lst)
HDF_TRGTS := $(subst lst,h5,$(LST_FILES))

HIST_ADC1 := $(subst .lst,_ADC1.pdf,$(LST_FILES))
HIST_ADC2 := $(subst .lst,_ADC2.pdf,$(LST_FILES))
HIST_ADC3 := $(subst .lst,_ADC3.pdf,$(LST_FILES))
HIST_ADC2_ADC1 := $(subst .lst,_ADC2_ADC1.pdf,$(LST_FILES))
HIST_ADC2_ADC3_DR2 := $(subst .lst,_ADC2_ADC3_DR2.pdf,$(LST_FILES))
HISTS := $(HIST_ADC1) $(HIST_ADC2) $(HIST_ADC3) $(HIST_ADC2_ADC1) $(HIST_ADC2_ADC3_DR2)

ROI_DR1 := $(subst lst,_DR1.h5roi,$(LST_FILES))
ROIS := $(ROI_DR1)


.PHONY : h5files histograms clean all

all : h5files rois histograms
h5files : $(HDF_TRGTS)
rois : h5files $(ROIS)
histograms : rois $(HISTS)


# clean : cleanplots
# 	rm mendeley_filtered.bib

%.h5 : %.lst
	$(PYTHON) -m $(LST2HDF5) $< --yes --out $@

%_DR1.h5roi : %.h5
	$(PYTHON) -m $(GENERATE_ROI) $< ADC1 --strip 5500 7500 --out $@

%_ADC1.pdf : %.h5
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC1 --pdf --png --out $@

%_ADC2.pdf : %.h5
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --pdf --png --out $@

%_ADC3.pdf : %.h5
	# some early files don't have ADC3 -> leading dash forces 'make' to press on despite error
	-$(PYTHON) -m $(HIST_FROM_MPA) $< ADC3 --pdf --png --out $@

%_ADC2_ADC1.pdf : %.h5
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --ychannel ADC1 --pdf --png --out $@

%_ADC2_ADC3_DR1.pdf : %.h5 %_DR1.h5roi
	$(PYTHON) -m $(HIST_FROM_MPA) $< ADC2 --ychannel ADC3 --pdf --png --out $@ --roi $*_DR1.h5roi
