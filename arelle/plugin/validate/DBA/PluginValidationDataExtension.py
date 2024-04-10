"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from collections import defaultdict
from typing import cast

from arelle.ModelInstanceObject import ModelFact, ModelContext
from arelle.ModelValue import qname, QName
from arelle.ModelXbrl import ModelXbrl
from arelle.utils.PluginData import PluginData

NAMESPACE_CMN = 'http://xbrl.dcca.dk/cmn'
NAMESPACE_FSA = 'http://xbrl.dcca.dk/fsa'
NAMESPACE_GSD = 'http://xbrl.dcca.dk/gsd'
NAMESPACE_SOB = 'http://xbrl.dcca.dk/sob'


class PluginValidationDataExtension(PluginData):
    _contextFactMap: dict[str, dict[QName, ModelFact]] | None = None
    _reportingPeriodContexts: list[ModelContext] | None = None
    annualReportTypes: frozenset[str] = frozenset([
        'Årsrapport',
        'årsrapport',
        'Annual report'
    ])
    consolidatedSoloDimensionQn: QName = qname(f'{{{NAMESPACE_CMN}}}ConsolidatedSoloDimension')
    consolidatedMemberQn: QName = qname(f'{{{NAMESPACE_CMN}}}ConsolidatedMember')
    dateOfApprovalOfAnnualReportQn: QName = qname(f'{{{NAMESPACE_SOB}}}DateOfApprovalOfAnnualReport')
    dateOfExtraordinaryDividendDistributedAfterEndOfReportingPeriod: QName = \
        qname(f'{{{NAMESPACE_FSA}}}DateOfExtraordinaryDividendDistributedAfterEndOfReportingPeriod')
    dateOfGeneralMeetingQn: QName = qname(f'{{{NAMESPACE_GSD}}}DateOfGeneralMeeting')
    extraordinaryCostsQn: QName = qname(f'{{{NAMESPACE_FSA}}}ExtraordinaryCosts')
    extraordinaryIncomeQn: QName = qname(f'{{{NAMESPACE_FSA}}}ExtraordinaryIncome')
    extraordinaryResultBeforeTaxQn: QName = qname(f'{{{NAMESPACE_FSA}}}ExtraordinaryResultBeforeTax')
    informationOnTypeOfSubmittedReportQn: QName = qname(f'{{{NAMESPACE_GSD}}}InformationOnTypeOfSubmittedReport')
    positiveProfitThreshold: float = 1000
    precedingReportingPeriodEndDateQn = qname(f'{{{NAMESPACE_GSD}}}PredingReportingPeriodEndDate')  # Typo in taxonomy
    precedingReportingPeriodStartDateQn = qname(f'{{{NAMESPACE_GSD}}}PrecedingReportingPeriodStartDate')
    profitLossQn: QName = qname(f'{{{NAMESPACE_FSA}}}ProfitLoss')
    reportingPeriodEndDateQn: QName = qname(f'{{{NAMESPACE_GSD}}}ReportingPeriodEndDate')
    reportingPeriodStartDateQn: QName = qname(f'{{{NAMESPACE_GSD}}}ReportingPeriodStartDate')
    taxExpenseOnOrdinaryActivitiesQn: QName = qname(f'{{{NAMESPACE_FSA}}}TaxExpenseOnOrdinaryActivities')
    taxExpenseQn: QName = qname(f'{{{NAMESPACE_FSA}}}TaxExpense')
    typeOfReportingPeriodDimensionQn: QName = qname(f'{{{NAMESPACE_GSD}}}TypeOfReportingPeriodDimension')

    def contextFactMap(self, modelXbrl: ModelXbrl) -> dict[str, dict[QName, ModelFact]]:
        if self._contextFactMap is None:
            self._contextFactMap = defaultdict(dict)
            for fact in modelXbrl.facts:
                self._contextFactMap[fact.contextID][fact.qname] = fact
        return self._contextFactMap

    def getCurrentAndPreviousReportingPeriodContexts(self, modelXbrl: ModelXbrl) -> list[ModelContext]:
        """
        :return: Returns the most recent reporting period contexts (at most two).
        """
        contexts = self.getReportingPeriodContexts(modelXbrl)
        if not contexts:
            return contexts
        if len(contexts) > 2:
            return contexts[-2:]
        return contexts

    def getReportingPeriodContexts(self, modelXbrl: ModelXbrl) -> list[ModelContext]:
        """
        :return: A sorted list of contexts that match "reporting period" criteria.
        """
        if self._reportingPeriodContexts is not None:
            return self._reportingPeriodContexts
        contexts = []
        for context in modelXbrl.contexts.values():
            context = cast(ModelContext, context)
            if context.isInstantPeriod or context.isForeverPeriod:
                continue  # Reporting period contexts can't be instant/forever contexts
            if len(context.qnameDims) > 0:
                if context.qnameDims.keys() != {self.consolidatedSoloDimensionQn}:
                    continue  # Context is dimensionalized with something other than consolidatedSoloDimensionQn
                if context.dimMemberQname(self.consolidatedSoloDimensionQn) != self.consolidatedMemberQn:
                    continue  # Context is dimensionalized with the correct dimension but not member
            contexts.append(context)
        self._reportingPeriodContexts = sorted(contexts, key=lambda c: c.endDatetime)
        return self._reportingPeriodContexts
