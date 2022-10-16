#from ast import And, Assert, Bytes, Return
from typing import Final
from xml.etree.ElementTree import Comment

from pyteal import abi, TealType, Global, Int, Seq, App, Txn, Assert, Approve
from beaker.application import Application
from beaker.state import (
    ApplicationStateValue,
    DynamicApplicationStateValue,
    AccountStateValue
)
from beaker.decorators import external, internal, create, opt_in, Authorize
from beaker import consts


class CrowdfundingCampaignApp(Application):

    # global states
    creator: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Creator of the crowdfunding campaign.",
    )

    campaign_goal: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Minimum ALGO amount to be collect by the crowdfunding campaign.",
    )

    collected_funds: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Minimum ALGO amount to be collect by the crowdfunding campaign.",
    )

    funds_receiver: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="Address of the funds receiver (address specified by the Creator).",
    )

    total_backers: Final[ApplicationStateValue] = ApplicationStateValue( # TODO: Is it really necessary?
        stack_type=TealType.uint64,
        descr="Total number of backers for the campaign.",
    )

    fund_start_date: Final[ApplicationStateValue] = ApplicationStateValue( # UNIX timestamp
        stack_type=TealType.uint64,
        descr="UNIX timestamp of when the crowdfunding campaign starts.",
    )

    fund_end_date: Final[ApplicationStateValue] = ApplicationStateValue( # UNIX timestamp
        stack_type=TealType.uint64,
        descr="UNIX timestamp of when the crowdfunding campaign endss.",
    )

    total_milestones: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Crowdfunding campaign's total milestones (max 10 milestones).",
    )

    reached_milestone: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        default=Int(0xFFFFFFFFFFFFFFFF),
        descr="Current number of milestones reached.",
    )

    # TODO: use funds_per_milestone for storing the values
    # funds_per_milestone: Final[DynamicApplicationStateValue] = DynamicApplicationStateValue(
    #     stack_type=TealType.uint64,
    #     max_keys=10,
    #     descr="List of funds divided for each milestone (max 10 milestones)",
    # )

    funds_0_milestone: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Funds for 0 milestone",
    )
    
    funds_1_milestone: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Funds for 1st milestone",
    )

    campaign_state: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Current state of the crowdfunding campaign: \
        [funding:0, waiting_for_next_milestone:1, milestone_validation:2, ended:3].",
    )

    milestone_approval_app_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Application ID for the current milestone approval app.",
    )

    RNFT_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="ID for the R-NFT (Reward-NFT).",
    )

    reward_metadata: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        descr="IPFS metadata link about the reward (R-NFT) to be claimed by the user.",
    )

    # local states
    amount_backed: Final[AccountStateValue] = AccountStateValue(
        stack_type=TealType.uint64,
        descr="Total amount of ALGO backed to the campaign by single backer.",
    )

    @create
    def create(self,
        campaign_goal: abi.Uint64,
        funds_receiver: abi.String,
        fund_start_date: abi.Uint64,
        fund_end_date: abi.Uint64,
        reward_metadata: abi.String,
        total_milestones: abi.Uint8,
        funds_0_milestone: abi.Uint64,
        funds_1_milestone: abi.Uint64,
    ):
        return Seq(
            self.initialize_application_state(),
            self.campaign_goal.set(campaign_goal.get()),
            self.funds_receiver.set(funds_receiver.get()),
            self.fund_start_date.set(fund_start_date.get()),
            self.fund_end_date.set(fund_end_date.get()),
            self.reward_metadata.set(reward_metadata.get()),
            self.total_milestones.set(total_milestones.get()),

            # TODO: use funds_per_milestone for storing the values
            # self.set_funds_per_milestone_val(k=Int(0), v=funds_0_milestone.get()),
            # self.set_funds_per_milestone_val(k=Int(1), v=funds_0_milestone.get()), 
            self.funds_0_milestone.set(funds_0_milestone.get()),    
            self.funds_1_milestone.set(funds_1_milestone.get()),
        )

    @opt_in
    def opt_in(self):
        return Seq(
            self.initialize_account_state(),
        )

    @external(authorize=Authorize.opted_in(Global.current_application_id()))
    def fund(self, funding: abi.PaymentTransaction):
        return Seq(
            Assert(
               self.campaign_state.get() == Int(0), comment="campaign must be in funding phase"
            ),
            Assert(
                    funding.get().amount() >= consts.Algos(10), comment="must be greater then 10 algos"
            ),
            Assert(funding.get().receiver() == self.address, comment="must be to me"),
            Assert(self.amount_backed[Txn.sender()].get() == Int(0), comment="must have not yet funded"),

            self.amount_backed[Txn.sender()].set(funding.get().amount()),
            self.collected_funds.increment(self.amount_backed[Txn.sender()].get()),
            self.total_backers.increment(Int(1)),
            Approve(),
        )

    # def set_funds_per_milestone_val(self, k: abi.Uint8, v: abi.Uint64):
    #     return self.funds_per_milestone[k].set(v.get())

    # @internal(read_only=True)
    # def get_funds_per_milestone_val(self, k: abi.Uint8, *, output: abi.Uint64):
    #     return output.set(self.funds_per_milestone[k])

if __name__ == "__main__":

    approval_filename = "./build/crowdfunding-approval.teal"
    clear_filename = "./build/crowdfunding-clear.teal"
    interface_filename = "./build/crowdfunding-contract.json"
    
    app = CrowdfundingCampaignApp()

    # save TEAL and ABI in build folder
    with open(approval_filename, "w") as f:
        f.write(app.approval_program)

    with open(clear_filename, "w") as f:
        f.write(app.clear_program)

    import json
    with open(interface_filename, "w") as f:
        f.write(json.dumps(app.contract.dictify()))
    
    print('\n------------TEAL generation completed!------------\n')