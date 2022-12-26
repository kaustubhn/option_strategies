## Author : Prashant Srivastava
## Last Modified Date  : Dec 25th, 2022

from py5paisa import FivePaisaClient
import re
import datetime
import logging
import json
import argparse

import strikes_manager
import order_manager
import utils


def login(cred_file: str):
    with open(cred_file) as cred_fh:
        cred = json.load(cred_fh)

    client = FivePaisaClient(
        email=cred["email"], passwd=cred["passwd"], dob=cred["dob"], cred=cred
    )
    client.login()

    return client


def main(args) -> None:

    ## Setup logging
    logging.basicConfig(
        filename="daily_logs.txt",
        filemode="a",
        format="%(asctime)s.%(msecs)d %(funcName)20s() %(levelname)s %(message)s",
        datefmt="%A,%d/%m/%Y|%H:%M:%S",
        level=logging.DEBUG,
    )

    ## Some handy day separater tag as title
    logging.info(
        "STARTING ALGO TRADING WEEKLY OTPTIONS DATED: |%s|" % datetime.datetime.now()
    )

    logger = logging.getLogger(__name__)
    logger.info("Command Line Arguments : %s" % json.dumps(vars(args), indent=2))

    EXPIRY_DAY = 0
    now = int(datetime.datetime.now().timestamp())
    tag = "p0wss%d" % now

    config = {
        "CLOSEST_PREMINUM": args.closest_premium,
        "SL_FACTOR": args.stop_loss_factor,
        "QTY": args.quantity,
        "INDEX_OPTION": args.index,
    }

    ## For now simply log the current INDIAVIX
    ## A very high fix day should be avoided, though the premiums will be very high

    logger.info("INDIA VIX :%.2f" % utils.get_india_vix())

    monitor_tag = None
    client = login(cred_file=args.creds)
    sm = strikes_manager.StrikesManager(client=client, config=config)
    om = order_manager.Ordermanager(client=client, config=config)
    if args.tag != "" and args.monitor_target <= 0.0:
        om.debug_status(tag=args.tag)
        return
    elif args.pnl:
        mtom = om.pnl()
        logger.info("MTM = %.2f" % mtom)
        return

    logger.info("USING INDEX :%s" % config["INDEX_OPTION"])
    logger.info("USING CLOSEST PREMINUM :%f" % config["CLOSEST_PREMINUM"])
    logger.info("USING SL FACTOR:%f" % config["SL_FACTOR"])
    logger.info("USING QTY:%d" % config["QTY"])
    logger.info("USING CURRENT TIMESTAMP TAG:%s" % tag)
    strangles = sm.strangle_strikes(
        closest_price_thresh=config["CLOSEST_PREMINUM"], index=config["INDEX_OPTION"]
    )
    straddles = sm.straddle_strikes(index=config["INDEX_OPTION"])

    symbol_pattern = "%s\s(\d+)\s" % config["INDEX_OPTION"]
    logger.info("Symbol Pattern %s" % symbol_pattern)
    st = re.search(symbol_pattern, straddles["ce_name"])
    if st:
        EXPIRY_DAY = int(st.group(1))
    logger.info("Expiry day:%d" % EXPIRY_DAY)

    logger.info("Obtained Strangle Strikes:%s" % json.dumps(strangles, indent=2))
    logger.info("Obtained Straddle Strikes:%s" % json.dumps(straddles, indent=2))

    if not args.show_strikes_only and args.tag == "":
        if args.strangle:
            om.place_short(strangles, tag)
            om.place_short_stop_loss(tag)
            monitor_tag = tag
        if args.straddle:
            om.place_short(straddles, tag)
            om.place_short_stop_loss(tag)
            monitor_tag = tag
    if args.monitor_target > 0.0:
        if args.tag != "":
            monitor_tag = args.tag
        if monitor_tag:
            om.monitor(
                target=args.monitor_target, tag=monitor_tag, expiry_day=EXPIRY_DAY
            )
        else:
            logger.info("No recent order, please provide a tag")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--creds",
        required=False,
        default="creds.json",
        type=str,
        help="Credentials file for login to 5paisa account",
    )
    parser.add_argument(
        "-s",
        "--show-strikes-only",
        action="store_true",
        help="Show strikes only, do not place order",
    )
    parser.add_argument(
        "--monitor-target",
        required=False,
        type=float,
        default=-1.0,
        help="Keep polling for given target amount",
    )
    parser.add_argument(
        "-cp",
        "--closest_premium",
        default=7.0,
        type=float,
        required=False,
        help="Search the strangle strikes for provided closest premium",
    )
    parser.add_argument(
        "-sl",
        "--stop_loss_factor",
        default=1.55,
        type=float,
        required=False,
        help="Percent above the placed price for stop loss",
    )
    parser.add_argument(
        "-q",
        "--quantity",
        default=100,
        type=int,
        required=False,
        help="Quantity to short for Nifty (Lot size =50), for 1 lot say 50",
    )
    parser.add_argument(
        "--index",
        default="NIFTY",
        type=str,
        required=False,
        help="Index to trade (NIFTY/BANKNIFTY)",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="",
        required=False,
        help="Tag to print status of last order for given tag, if combined with --monitor_target it polls the position for given tag",
    )
    parser.add_argument("--pnl", action="store_true", help="Show current PNL")
    parser.add_argument("--strangle", action="store_true", help="Place Strangle")
    parser.add_argument("--straddle", action="store_true", help="Place Straddle")
    args = parser.parse_args()
    main(args)
