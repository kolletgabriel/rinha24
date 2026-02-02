#!/usr/bin/env python3

import json
import sys
from pathlib import Path


REPORTS_PREFIX = Path(Path(__file__).parent.parent, 'benchmarks', 'results').resolve()

FULL_PAYMENT = 100_000.0
SLA_MIN_PCT = 98.0
PENATY_BALANCE = 803.01
PENALTY_RESPONSETIME = 1000.0


def main(args: list[str]) -> None:
    simulation = simulation_report(args)
    logfile = Path(simulation, 'simulation.log')
    stats = Path(simulation, 'js', 'stats.json')

    num_balance_inconsistencies = balance_inconsistencies(logfile)
    pct_slow_responses = slow_responses(stats)
    total_penalty_balance = PENATY_BALANCE * num_balance_inconsistencies
    total_penalty_responsetime = PENALTY_RESPONSETIME * pct_slow_responses
    total_penalty_overall = total_penalty_balance + total_penalty_responsetime

    print(f'Inconsistencies in customer balance: {num_balance_inconsistencies}. Fine imposed: U$ {total_penalty_balance:,.2f}')
    print(f'Responses above 250ms: {pct_slow_responses:.2f}%. Fine imposed: U$ {total_penalty_responsetime:,.2f}')
    print(f'Total fine imposed: U$ {total_penalty_overall:,.2f}')
    print(f'Amount received: U$ {FULL_PAYMENT - total_penalty_overall:,.2f}')


def dir_is_report(path: Path) -> bool:
    '''Validate if the given `path` is a proper simulation report directory.'''

    has_logs = Path(path, 'simulation.log').exists()
    has_stats = Path(path, 'js', 'stats.json').exists()
    return has_logs and has_stats


def simulation_report(argv: list[str]) -> Path:
    '''Get the `Path` for the provided simulation. If nothing was provided, get
    the `Path` for the last one.'''

    if len(argv) >= 1:  # ignore surplus arguments
        simulation = REPORTS_PREFIX / Path(argv[0]).name
        if not dir_is_report(simulation):
            raise FileNotFoundError
        return simulation

    simulations = [
        s for s in sorted(REPORTS_PREFIX.iterdir())
        if dir_is_report(s)
    ]
    if len(simulations) == 0:
        raise FileNotFoundError

    return simulations[-1]


def balance_inconsistencies(logs: Path) -> int:
    '''Counts the total number of inconsistencies in customer balances.'''

    with open(logs, 'r') as file:
        text = file.read()

    pattern1 = text.count('jmesPath(saldo.total).find.is')
    pattern2 = text.count('ConsistenciaSaldoLimite')
    return pattern1 + pattern2


def slow_responses(stats: Path) -> float:
    '''Fetches the % of responses that took over 250ms to reach the client.'''

    with open(stats) as file:
        pct = json.load(file)['stats']['group1']['percentage']

    return max(0.0, (SLA_MIN_PCT - pct))


if __name__ == '__main__':
    main(sys.argv[1:])
