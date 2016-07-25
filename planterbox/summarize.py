"""nose2 plugin for collecting and summarizing results of planterbox tests"""

from itertools import (
    groupby,
)

from nose2.events import (
    Plugin,
)


class PlanterboxSummary(Plugin):
    configSection = 'planterbox-summary'
    commandLineSwitch = (None, 'with-planterbox-summary',
                         'Summarize failed .feature tests after run')

    SUMMARY_HEADERS = (
        ('failures', 'Failures'),
        ('errors', 'Errors'),
    )

    def beforeSummaryReport(self, event):
        from planterbox.feature import FeatureTestCase, FeatureExcInfo

        for key, header in self.SUMMARY_HEADERS:
            reportable_results = [
                result for result in event.reportCategories[key]
                if isinstance(result.test, FeatureTestCase)
                and isinstance(result.exc_info, FeatureExcInfo)
            ]
            if not reportable_results:
                continue
            event.stream.write(header + '\n' + '=' * len(header) + '\n')
            self.summarize_features(event, reportable_results)

    def summarize_features(self, event, reportable_results):
        grouped_features = groupby(
            sorted(reportable_results,
                   key=(lambda r: (r.test.feature_id,
                                   r.exc_info.scenario_index)
                        )),
            (lambda r: r.test)
        )
        for test, results in grouped_features:
            event.stream.write('Feature: ' + test.feature_name + '\n')
            for result in results:
                event.stream.write('{}\n  {}:{}\n'.format(
                    result.exc_info.scenario_name.strip(),
                    test.feature_id(),
                    result.exc_info.scenario_index,
                ))
            event.stream.write('\n')
