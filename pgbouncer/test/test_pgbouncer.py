# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
import time
from types import ListType

# 3p
from nose.plugins.attrib import attr
try:
    import psycopg2 as pg
except ImportError:
    pg = None

# project
from tests.checks.common import AgentCheckTest


@attr(requires='pgbouncer')
class TestPgbouncer(AgentCheckTest):
    CHECK_NAME = 'pgbouncer'

    def test_checks(self):
        pgbouncer_version = os.environ.get('FLAVOR_VERSION', 'latest')
        pgbouncer_pre18 = pgbouncer_version in ('1.5', '1.7')

        config = {
            'init_config': {},
            'instances': [
                {
                    'host': 'localhost',
                    'port': 16432,
                    'username': 'datadog',
                    'password': 'datadog',
                    'tags': ['optional:tag1']
                },
                {
                    'database_url': 'postgresql://datadog:datadog@localhost:16432/datadog_test',
                    'tags': ['optional:tag1']
                }
            ]
        }

        try:
            connection = pg.connect(
                host='localhost',
                port='16432',
                user='datadog',
                password='datadog',
                database='datadog_test')
            connection.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = connection.cursor()
            cur.execute('SELECT * FROM persons;')
        except Exception:
            pass
        self.run_check(config)

        self.assertMetric('pgbouncer.pools.cl_active')
        self.assertMetric('pgbouncer.pools.cl_waiting')
        self.assertMetric('pgbouncer.pools.sv_active')
        self.assertMetric('pgbouncer.pools.sv_idle')
        self.assertMetric('pgbouncer.pools.sv_used')
        self.assertMetric('pgbouncer.pools.sv_tested')
        self.assertMetric('pgbouncer.pools.sv_login')
        self.assertMetric('pgbouncer.pools.maxwait')

        self.assertMetric('pgbouncer.stats.avg_recv')
        self.assertMetric('pgbouncer.stats.avg_sent')

        if pgbouncer_pre18:
            self.assertMetric('pgbouncer.stats.avg_req')
            self.assertMetric('pgbouncer.stats.avg_query')
        else:
            self.assertMetric('pgbouncer.stats.avg_transaction_time')
            self.assertMetric('pgbouncer.stats.avg_query_time')
            self.assertMetric('pgbouncer.stats.avg_transaction_count')
            self.assertMetric('pgbouncer.stats.avg_query_count')

        # Rate metrics, need 2 collection rounds
        try:
            connection = pg.connect(
                host='localhost',
                port='16432',
                user='datadog',
                password='datadog',
                database='datadog_test')
            connection.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = connection.cursor()
            cur.execute('SELECT * FROM persons;')
        except Exception:
            pass
        time.sleep(1)
        self.run_check(config)
        if pgbouncer_pre18:
            self.assertMetric('pgbouncer.stats.requests_per_second')
        else:
            self.assertMetric('pgbouncer.stats.queries_per_second')
            self.assertMetric('pgbouncer.stats.transactions_per_second')
            self.assertMetric('pgbouncer.stats.total_transaction_time')
        self.assertMetric('pgbouncer.stats.total_query_time')
        self.assertMetric('pgbouncer.stats.bytes_received_per_second')
        self.assertMetric('pgbouncer.stats.bytes_sent_per_second')

        # Service checks
        service_checks_count = len(self.service_checks)
        self.assertTrue(isinstance(self.service_checks, ListType))
        self.assertTrue(service_checks_count > 0)
        self.assertServiceCheckOK(
            'pgbouncer.can_connect',
            tags=['host:localhost', 'port:16432', 'db:pgbouncer', 'optional:tag1'],
            count=service_checks_count)
