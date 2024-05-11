import numpy as np
import pandas as pd
import json
import time
import random
import copy
from typing import *
import util
import datetime
import csp_solver as csp
from date_constraints import DateConstraint as DC

# Training / Testing
WEIGHT_PATH = "./example_weights.json"

TRAINING = True
# TRAINING = False

CLEAR_WEIGHTS = True
# CLEAR_WEIGHTS = False

# Training Paramaters
EPSILON = 0.2
DISCOUNT = 0.8
LEARNING_RATE = 0.1

class OliveCalendar:
    def __init__(self: "OliveCalendar") -> None:
        self.events: list[dict[str, Union[float, "datetime.time", int, bool]]] = []
        self.past_events: list[dict[str, Union[float, "datetime.time", int, bool]]] = []
        self.illegal_times: list[datetime.time] = []
        self.illegal_event_times: dict[str, tuple[datetime.time, datetime.time]] = {}

    def add_event(
        self: "OliveCalendar",
        event: dict[str, Union[float, "datetime.time", int, bool]],
    ) -> None:
        if self.check_legal(event):
            self.events.append(event)
        else:
            raise TypeError(
                "This addition results in an event collision with strictly-scheduled events."
            )

    def remove_event(
        self: "OliveCalendar",
        event: dict[str, Union[float, "datetime.time", int, bool]],
    ) -> None:
        if event in self.events:
            self.events.remove(event)
        else:
            raise ValueError("This event is not already in the calendar.")

    def get_legal_actions(
        self: "OliveCalendar",
    ) -> list[datetime.datetime]:
        constraints: set["DC"] = set()
        for event in self.events:
            constraint_start = DC(0, "!=", event["start"])
            constraint_end = DC(0, "!=", event["end"])
            constraints.add(constraint_start)
            constraints.add(constraint_end)
        tomorrow: datetime.datetime = datetime.now() + datetime.timedelta(days=1)
        dates: set[datetime.datetime] = DC.generate_dates(tomorrow, (event["deadline"] - tomorrow).days)
        legal_times: list[datetime.datetime] = [time for time in csp.solve(1, dates, constraints) if time not in self.illegal_times]
        return legal_times
    
    # Implement
    def check_legal(self: "OliveCalendar") -> bool:
        pass

    def get_successor(
        self: "OliveCalendar",
        event: dict[str, Union[float, "datetime.time", int, bool]],
    ) -> "OliveCalendar":
        successor_state = copy.deepcopy(self)
        successor_state.add_event(event)
        return successor_state

    # Need to complete overriding hash
    def __hash__(self: "OliveCalendar") -> float:
        val: float = 0
        for event in self.events:
            val += event["priority"]
            val += len(event["name"])
            if not event["task"]:
                val /= self.events["start"]
        return val

    def __eq__(self: "OliveCalendar", other: "OliveCalendar") -> bool:
        if len(self.events) != len(other.events):
            return False
        # Check every event attribute
        for self_event_attr, other_event_attr in zip(self.events, other.events):
            if self_event_attr != other_event_attr:
                return False
        return True

class FeatureExtractor:
    def get_features(self: "FeatureExtractor") -> dict[str, int]:
        return util.raiseNotDefined()

class BasicCalendarExtractor(FeatureExtractor):
    def get_features(self: "BasicCalendarExtractor", calendar: "OliveCalendar", proposed_event: dict[str, Union[float, "datetime.time", int, bool]]) -> dict[str, int]:
        features: dict[str, int] = util.Counter()
        calendar.add_event(proposed_event)
        for event in calendar.events:
            if event["task"]:
                features[f"{"Task"}, {event["type"]}, {str((event["deadline"] - event["start"]).days)}"] = 1
            else:
                features[f"{"Non-task"}, {event["type"]}, {str(event["start"].hour)}, {str(event["end"].hour)}"] = 1
        return features

# Need to implement
class OliveEvent:
    pass
    
class OliveRL:
    def __init__(self: "OliveRL") -> None:
        pass

    def initialize_weights(self: "OliveRL") -> None:
        if TRAINING:
            with open(WEIGHT_PATH, "r") as weight_file:
                agent_weights = json.load(weight_file)
                WEIGHTS_PRESENT = True if agent_weights else False

            if WEIGHTS_PRESENT:
                self.weights = util.Counter(agent_weights)
            else:
                self.weights: dict[str, float] = util.Counter()
        else:
            with open(WEIGHT_PATH, "r") as json_file:
                agent_weights = util.Counter(json.load(json_file))
                self.weights: dict[str, float] = agent_weights
    
    def update_weights(self: "OliveRL") -> None:
        pass

    def get_successor(self: "OliveRL", cal_state: "OliveCalendar", event: dict[str, Union[float, "datetime.time", int, bool]]) -> "OliveCalendar":
        next_cal_state: "OliveCalendar" = cal_state.get_successor(event)
        return next_cal_state
    
    def get_features(self: "OliveRL", cal_state: "OliveCalendar") -> dict[str, float]:
        features: dict[str, float] = BasicCalendarExtractor.get_features(cal_state)
        return features

    def get_q_value(self: "OliveRL", cal_state: "OliveCalendar") -> float:
        features: dict[str, int] = self.get_features(cal_state)
        return features * self.weights
    
    def get_feedback(self: "OliveRL", event: dict[str, Union[float, "datetime.time", int, bool]]) -> int:
        task_rating = input(f"How did you feel about the task/event {event['name']}? Give a rating between 0 and 3.")
        return task_rating
    
    def get_reward(self: "OliveRL", curr_cal_state: "OliveCalendar", proposed_event: dict[str, Union[float, "datetime.time", int, bool]], next_cal_state: "OliveCalendar") -> float:
        reward: float = 0
        for event in next_cal_state.past_events:
            match self.get_feedback(event):
                case 0:
                    next_cal_state.illegal_event_times[event["type"]] = (event["start"], event["end"])
                case 1:
                    reward -= 0.1
                case 2:
                    reward += 0
                case 3:
                    reward += 0.1
        return reward