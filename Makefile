PYTHON = python
LST2HDF5 = lst2hdf5
HISTFROMMPA = histfrommpa

LST_DIR := /run/media/hpahl/HannesExtHDD/Fe_DR_TimeResolvedJuly2020
LST_FILES := $(wildcard $(LST_DIR)/*.lst)
HDF_TRGTS := $(subst lst,h5,$(LST_FILES))
HIST_ADC1_TRGTS := $(subst .lst,_ADC1.pdf,$(LST_FILES))
HIST_ADC2_TRGTS := $(subst .lst,_ADC2.pdf,$(LST_FILES))
HIST_ADC3_TRGTS := $(subst .lst,_ADC3.pdf,$(LST_FILES))
HIST_ADC2_ADC1_TRGTS := $(subst .lst,_ADC2_ADC1.pdf,$(LST_FILES))


.PHONY : h5files histograms clean all

h5files : $(HDF_TRGTS)

histograms : $(HIST_ADC1_TRGTS) $(HIST_ADC2_TRGTS) $(HIST_ADC3_TRGTS) $(HIST_ADC2_ADC1_TRGTS)

all : h5files histograms

# clean : cleanplots
# 	rm mendeley_filtered.bib

%.h5 : %.lst
	$(PYTHON) -m $(LST2HDF5) --yes --out $@ $<

%_ADC1.pdf : %.h5
	$(PYTHON) -m $(HISTFROMMPA) $< ADC1 --pdf --png --out $@

%_ADC2.pdf : %.h5
	$(PYTHON) -m $(HISTFROMMPA) $< ADC2 --pdf --png --out $@

%_ADC3.pdf : %.h5
	$(PYTHON) -m $(HISTFROMMPA) $< ADC3 --pdf --png --out $@

%_ADC2_ADC1.pdf : %.h5
	$(PYTHON) -m $(HISTFROMMPA) $< ADC2 --ychannel ADC1 --pdf --png --out $@