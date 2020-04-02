'''
instanceInfo.py provides information about an XBRL instance

(c) Copyright 2018 Mark V Systems Limited, All rights reserved.
'''
import sys, os, time, math, logging
from collections import defaultdict
from arelle.ValidateXbrlCalcs import inferredDecimals, rangeValue
from arelle import ModelDocument

memoryAtStartup = 0
timeAtStart = 0

def startup(cntlr, options, *args, **kwargs):
    global memoryAtStartup, timeAtStart
    memoryAtStartup = cntlr.memoryUsed
    timeAtStart = time.time()
    
def showInfo(cntlr, options, modelXbrl, _entrypoint, *args, **kwargs):
    for url, doc in sorted(modelXbrl.urlDocs.items(), key=lambda i: i[0]):
        cntlr.addToLog("File {} size {:,}".format(doc.basename, os.path.getsize(doc.filepath)), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Heap memory before loading {:,}".format(memoryAtStartup), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Heap memory after loading {:,}".format(cntlr.memoryUsed), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Time to load {:.2f} seconds".format(time.time() - timeAtStart), messageCode="info", level=logging.DEBUG)
    isInlineXbrl = modelXbrl.modelDocument.type in (ModelDocument.Type.INLINEXBRL, ModelDocument.Type.INLINEXBRLDOCUMENTSET)
    if isInlineXbrl:
        instanceType = "inline XBRL, number of documents {}".format(len(modelXbrl.ixdsHtmlElements))
    else:
        instanceType = "xBRL-XML"
    cntlr.addToLog("Instance type {}".format(instanceType), messageCode="info", level=logging.DEBUG)
    numContexts = len(modelXbrl.contexts)
    numLongContexts = 0
    bytesSaveable = 0
    frequencyOfDims = {}
    sumNumDims = 0
    distinctDurations = set()
    distinctInstants = set()
    shortContextIdLen = int(math.log10(numContexts)) + 2
    for c in modelXbrl.contexts.values():
        sumNumDims += len(c.qnameDims)
        for d in c.qnameDims.values():
            frequencyOfDims[str(d.dimensionQname)] = frequencyOfDims.get(str(d.dimensionQname),0) + 1
        if c.isInstantPeriod:
            distinctInstants.add(c.instantDatetime)
        elif c.isStartEndPeriod:
            distinctDurations.add((c.startDatetime, c.endDatetime))
        if len(c.id) > shortContextIdLen:
            bytesSaveable += len(c.id) - shortContextIdLen
    cntlr.addToLog("Number of contexts {:,}".format(numContexts), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Number of distinct durations {:,}".format(len(distinctDurations)), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Number of distinct instants {:,}".format(len(distinctInstants)), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Avg number dimensions per contexts {:,.2f}".format(sumNumDims/numContexts), messageCode="info", level=logging.DEBUG)
    mostPopularDims = sorted(frequencyOfDims.items(), key=lambda i:"{:0>9},{}".format(999999999-i[1],i[0]))
    for dimName, count in mostPopularDims[0:3]:
        cntlr.addToLog("Dimension {} used in {:,} contexts".format(dimName, count), messageCode="info", level=logging.DEBUG)
    numFacts = 0
    numTableTextBlockFacts = 0
    lenTableTextBlockFacts = 0
    numContinuations = 0
    maxLenContinuation = 0
    numTextBlockFacts = 0
    lenTextBlockFacts = 0
    distinctElementsInFacts = set()
    factsPerContext = {}
    factForConceptContextUnitLangHash = defaultdict(list)
    for f in modelXbrl.factsInInstance:
        context = f.context
        concept = f.concept
        distinctElementsInFacts.add(f.qname)
        numFacts += 1
        if f.qname.localName.endswith("TableTextBlock"):
            numTableTextBlockFacts += 1
            lenTableTextBlockFacts += len(f.xValue)
        elif f.qname.localName.endswith("TextBlock"):
            numTextBlockFacts += 1
            lenTextBlockFacts += len(f.xValue)
        if f.get("continuedAt"):
            numContinuations += 1
            maxLenContinuation = max(maxLenContinuation, len(f.xValue))
        if context is not None and concept is not None:
            factsPerContext[context.id] = factsPerContext.get(context.id,0) + 1
            factForConceptContextUnitLangHash[f.conceptContextUnitLangHash].append(f)
            bytesSaveable += len(context.id) - shortContextIdLen
        
    mostPopularContexts = sorted(factsPerContext.items(), key=lambda i:"{:0>9},{}".format(999999999-i[1],i[0]))
    cntlr.addToLog("Number of facts {:,}".format(numFacts), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Number of TableTextBlock facts {:,} avg len {:,.0f}".format(numTableTextBlockFacts, lenTableTextBlockFacts/numTableTextBlockFacts), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Number of TextBlock facts {:,} avg len {:,.0f}".format(numTextBlockFacts, lenTextBlockFacts/numTableTextBlockFacts), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Number of continuation facts {:,} max len {:,.0f}".format(numContinuations, maxLenContinuation), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Max number facts per context {:,}".format(mostPopularContexts[0][1]), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Avg number facts per context {:,.2f}".format(sum([v for v in factsPerContext.values()])/numContexts), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Distinct elements in facts {:,}".format(len(distinctElementsInFacts)), messageCode="info", level=logging.DEBUG)
    cntlr.addToLog("Number of bytes saveable context id of {} length is {:,}".format(shortContextIdLen, bytesSaveable), messageCode="info", level=logging.DEBUG)

    aspectEqualFacts = defaultdict(list)
    numConsistentDupFacts = numInConsistentDupFacts = 0
    for hashEquivalentFacts in factForConceptContextUnitLangHash.values():
        if len(hashEquivalentFacts) > 1:
            for f in hashEquivalentFacts:
                aspectEqualFacts[(f.qname,f.contextID,f.unitID,f.xmlLang)].append(f)
            for fList in aspectEqualFacts.values():
                f0 = fList[0]
                if f0.concept.isNumeric:
                    if any(f.isNil for f in fList):
                        _inConsistent = not all(f.isNil for f in fList)
                    elif all(inferredDecimals(f) == inferredDecimals(f0) for f in fList[1:]): # same decimals
                        v0 = rangeValue(f0.value)
                        _inConsistent = not all(rangeValue(f.value) == v0 for f in fList[1:])
                    else: # not all have same decimals
                        aMax, bMin = rangeValue(f0.value, inferredDecimals(f0))
                        for f in fList[1:]:
                            a, b = rangeValue(f.value, inferredDecimals(f))
                            if a > aMax: aMax = a
                            if b < bMin: bMin = b
                        _inConsistent = (bMin < aMax)
                else:
                    _inConsistent = any(not f.isVEqualTo(f0) for f in fList[1:])
                if _inConsistent:
                    numInConsistentDupFacts += 1
                else:
                    numConsistentDupFacts += 1
            aspectEqualFacts.clear()
    cntlr.addToLog("Number of duplicate facts consistent {:,} inconsistent {:,}".format(numConsistentDupFacts, numInConsistentDupFacts), messageCode="info", level=logging.DEBUG)
    
    styleAttrCounts = {}
    for ixdsHtmlRootElt in modelXbrl.ixdsHtmlElements: # ix root elements
        for ixElt in ixdsHtmlRootElt.iterdescendants():
            style = ixElt.get("style")
            if style:
                styleAttrCounts[style] = styleAttrCounts.get(style,0) + 1
    numDupStyles = sum(1 for n in styleAttrCounts.values() if n > 1)
    bytesSaveableByCss = sum(len(s)*(n-1) for s,n in styleAttrCounts.items() if n > 1)
    cntlr.addToLog("Number of duplicate styles {:,} bytes saveable by CSS {:,}".format(numDupStyles, bytesSaveableByCss), messageCode="info", level=logging.DEBUG)
    
    
__pluginInfo__ = {
    'name': 'Instance Info',
    'version': '1.0',
    'description': "This plug-in displays instance information for sizing and performance issues.",
    'license': 'Apache-2',
    'author': 'Mark V Systems Limited',
    'copyright': '(c) Copyright 2020 Mark V Systems Limited, All rights reserved.',
    # classes of mount points (required)
    'CntlrCmdLine.Filing.Start': startup,
    'CntlrCmdLine.Xbrl.Loaded': showInfo
}
