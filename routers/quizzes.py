import re
import os
from typing import Annotated
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import motor.motor_asyncio

class Question:
    def __init__(self, text: str, options: list[str], correct_answer: str):
        self.text = text
        self.correct_answer = correct_answer
        self.options = options
    def check_answer(self, answer: str):
        if answer == self.correct_answer and answer in self.options:
            return True
        else:
            return False
        
class Quiz:
    def __init__(self, questions: list[Question] = None, score = 0, file = None):
        self.questions = questions
        self.score = score
    def score_quiz(self, answers: list[str]):
        correct_count = 0
        quiz_len = len(self.questions)

        for question in self.questions:
            #print(question.text)
            for answer in answers:
                # print(answer)
                # print(question.correct_answer.replace("Answer: ", ""))
                if answer in question.correct_answer.replace("Answer: ", ""):
                    # print("Correct!")
                    correct_count +=1
                else:
                    continue
        # print(correct_count)
        # print(quiz_len)
        score = (correct_count/quiz_len)*100
        return score
    def from_file(self, file):
        self.questions = []
        with open(file, "r") as quiz_file:
            file_contents = quiz_file.readlines()
            # file_split = re.split("\n", file_contents)
            # file_string = ''.join(file_split)

            
            question = Question(None, [], None)
            for line in file_contents:
                
                # print(line)
                question_search = re.search(r"Question:", line)
                answer_search = re.search(r"Answer:", line)
                option_search = re.search(r"Option:", line)

                if question_search:
                    question.text = question_search.string.replace("Question:", "")
                if option_search:
                    question.options.append(option_search.string.replace("Option:", "").replace("\n", ""))
                if answer_search:
                    question.correct_answer = answer_search.string.replace("Answer:", "")
                
                if line == "\n":
                    self.questions.append(question)
                    question = Question(None, [], None)
                    
