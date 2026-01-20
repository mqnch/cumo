import dateparser
import parsedatetime
import spacy
from datetime import datetime
from typing import Dict, Optional, Any

from .rules import (
    extract_explicit_time,
    extract_relative_time,
    extract_time_range,
    normalize_text,
    merge_datetime_time
)


class Parser:
    TEMPORAL_PATTERNS = ['DATE', 'TIME']
    
    COMMAND_VERBS = {
        'set', 'create', 'schedule', 'add', 'make', 'plan', 'book',
        'put', 'establish', 'arrange', 'organize', 'setup'
    }
    
    TEMPORAL_WORDS = {
        'tomorrow', 'tmr', 'today', 'tdy', 'yesterday', 'yest', 'now', 'tonight',
        'monday', 'mon', 'tuesday', 'tue', 'wednesday', 'wed', 'thursday', 'thu', 'friday', 'fri', 'saturday', 'sat', 'sunday', 'sun',
        'january', 'jan', 'february', 'feb', 'march', 'mar', 'april', 'apr', 'may', 'june', 'jun',
        'july', 'jul', 'august', 'aug', 'september', 'sep', 'october', 'oct', 'november', 'nov', 'december', 'dec',
        'am', 'pm', 'noon', 'midnight', 'at', '@', 'in', 'on', 'next', 'this', 'last',
        'remind', 'me', 'to', 'night'
    }
    
    TIME_UNITS = {
        'hour', 'hours', 'minute', 'minutes', 'day', 'days', 
        'week', 'weeks', 'month', 'months', 'year', 'years'
    }
    
    NUMBER_WORDS = {
       'zero' 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
        'twenty', 'thirty', 'forty', 'fifty'
    }
    
    GENERIC_NOUNS = {
        'event', 'meeting', 'appointment', 'reminder', 'call', 'task'
    }
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Please install it with: python -m spacy download en_core_web_sm"
            )
        self.cal = parsedatetime.Calendar()
    
    
    def detect_intent(self, text: str) -> str:
        normalized = normalize_text(text)
        if normalized.startswith("remind me"):
            return "reminder"
        return "event"
    

    def extract_datetime(self, text: str) -> Optional[datetime]:
        base_date = datetime.now()
        
        parsed = dateparser.parse(text, settings={'RELATIVE_BASE': base_date})
        if parsed:
            return parsed
        
        result, status = self.cal.parseDT(text, sourceTime=base_date)
        if status > 0:  
            return result
        
        relative_dt = extract_relative_time(text, base_date)
        if relative_dt:
            return relative_dt
        
        return None
    

    def extract_time(self, text: str, date_obj: Optional[datetime] = None) -> Optional[tuple]:
        if date_obj is None:
            date_obj = datetime.now()

        time_range = extract_time_range(text, date_obj)
        if time_range:
            return time_range[0]
        
        has_time = date_obj.hour != 0 or date_obj.minute != 0
        explicit_time = extract_explicit_time(text, date_obj)
        
        if explicit_time:
            return explicit_time
        if has_time:
            return None
        return None
    

    def _identify_tokens_to_skip(self, doc) -> set:
        tokens_to_skip = set()
        
        for i, token in enumerate(doc):
            token_lower = token.text.lower()
            
            if token.ent_type_ in self.TEMPORAL_PATTERNS:
                tokens_to_skip.add(i)
                continue
            if token_lower in self.TEMPORAL_WORDS:
                tokens_to_skip.add(i)
                continue
            if token_lower in self.COMMAND_VERBS:
                tokens_to_skip.add(i)
                continue
            if self._should_skip_article(token, i, doc):
                tokens_to_skip.add(i)
                continue
            
            time_phrase_indices = self._get_time_phrase_indices(token, i, doc)
            tokens_to_skip.update(time_phrase_indices)
        
        return tokens_to_skip
    

    def _should_skip_article(self, token, i, doc) -> bool:
        token_lower = token.text.lower()
        if token_lower not in ['an', 'a', 'the']:
            return False
        if i > 0 and doc[i-1].text.lower() in self.COMMAND_VERBS:
            return True
        if i < len(doc) - 1:
            next_token = doc[i+1]
            if next_token.text.lower() in self.GENERIC_NOUNS:
                return True  
        return False
    

    def _get_time_phrase_indices(self, token, i, doc) -> set:
        indices = set()
        
        if token.like_num:
            if i < len(doc) - 1:
                next_token = doc[i+1]
                if next_token.text.lower() in self.TIME_UNITS:
                    indices.add(i)
                    indices.add(i+1)
                    if i > 0 and doc[i-1].text.lower() == 'in':
                        indices.add(i-1)           
            if i < len(doc) - 2:
                next_token = doc[i+1]
                next_next = doc[i+2]
                if next_token.text.lower() in ['-', 'to'] and next_next.like_num:
                    if i < len(doc) - 3:
                        next_next_next = doc[i+3]
                        if next_next_next.text.lower() in ['am', 'pm']:
                            indices.add(i)
                            indices.add(i+1)
                            indices.add(i+2)
                            indices.add(i+3)
            return indices
        
        if token.text.lower() == 'in' and i < len(doc) - 2:
            next_token = doc[i+1]
            next_next = doc[i+2]
            if (next_token.like_num or next_token.text.lower() in self.NUMBER_WORDS):
                if next_next.text.lower() in self.TIME_UNITS:
                    indices.add(i)
                    indices.add(i+1)
                    indices.add(i+2)
        if token.text.lower() == 'at' and i < len(doc) - 1:
            next_token = doc[i+1]
            if next_token.text.lower() == 'night':
                indices.add(i)
                indices.add(i+1)
        return indices


    def _extract_infinitive_phrases(self, doc) -> set:
        infinitive_phrase_tokens = set()
        
        for token in doc:
            if token.dep_ != "mark" or token.text.lower() != "to":
                continue

            infinitive_verb = token.head
            if infinitive_verb.pos_ != "VERB":
                continue
            
            infinitive_phrase_tokens.add(infinitive_verb.i)
            
            for child in infinitive_verb.children:
                if child.dep_ in ["dobj", "pobj", "attr", "acomp", "nsubj", "nsubjpass"]:
                    infinitive_phrase_tokens.add(child.i)
                    self._add_phrase_children(child, infinitive_phrase_tokens)
                elif child.dep_ == "prep":
                    infinitive_phrase_tokens.add(child.i)
                    for prep_child in child.children:
                        if prep_child.dep_ == "pobj":
                            infinitive_phrase_tokens.add(prep_child.i)
        
        return infinitive_phrase_tokens
    

    def _add_phrase_children(self, token, phrase_tokens):
        for child in token.children:
            if child.dep_ in ["prep", "pobj", "amod", "compound"]:
                phrase_tokens.add(child.i)
                for gg_child in child.children:
                    if gg_child.dep_ in ["pobj", "amod"]:
                        phrase_tokens.add(gg_child.i)
    

    def _build_title_from_tokens(self, doc, tokens_to_skip, infinitive_tokens) -> Optional[str]:
        if not infinitive_tokens:
            return None
        
        title_tokens = []
        for i, token in enumerate(doc):
            if i in tokens_to_skip:
                continue
            if i in infinitive_tokens:
                title_tokens.append(token.text)
        
        title = ' '.join(title_tokens).strip()
        return title if title else None
    

    def _build_title_fallback(self, doc, tokens_to_skip) -> str:
        title_tokens = []
        for i, token in enumerate(doc):
            if i in tokens_to_skip:
                continue
            
            if token.pos_ in ['NOUN', 'VERB', 'PROPN', 'ADJ'] or token.is_alpha:
                if len(token.text) > 1 or token.text.lower() in ['i', 'a']:
                    title_tokens.append(token.text)
        
        return ' '.join(title_tokens).strip()
    

    def _filter_words_fallback(self, text) -> str:
        words = text.split()
        filtered = []
        skip_indices = set()
        
        for i, word in enumerate(words):
            word_lower = word.lower()
            
            if word_lower in self.TEMPORAL_WORDS or word_lower in self.COMMAND_VERBS:
                skip_indices.add(i)
                continue
            
            if word_lower in ['an', 'a', 'the'] and i > 0:
                if words[i-1].lower() in self.COMMAND_VERBS:
                    skip_indices.add(i)
                    continue
            
            if word_lower == 'at' and i < len(words) - 1:
                if words[i+1].lower() == 'night':
                    skip_indices.add(i)
                    skip_indices.add(i+1)
                    continue
            
            if word_lower in self.TIME_UNITS and i > 0:
                if words[i-1].isdigit() or words[i-1].lower() in self.NUMBER_WORDS:
                    skip_indices.add(i)
                    skip_indices.add(i-1)
                    if i > 1 and words[i-2].lower() == 'in':
                        skip_indices.add(i-2)
                    continue
            
            if word.isdigit() and i < len(words) - 1:
                if words[i+1].lower() in self.TIME_UNITS:
                    skip_indices.add(i)
                    continue
                
                if words[i+1].lower() in ['-', 'to'] and i < len(words) - 2:
                    if words[i+2].isdigit() and i < len(words) - 3:
                        if words[i+3].lower() in ['am', 'pm']:
                            skip_indices.add(i)
                            skip_indices.add(i+1)
                            skip_indices.add(i+2)
                            skip_indices.add(i+3)
                            continue
            
            if word_lower in ['-', 'to'] and i > 0 and i < len(words) - 1:
                if words[i-1].isdigit() and words[i+1].isdigit():
                    if i < len(words) - 2 and words[i+2].lower() in ['am', 'pm']:
                        skip_indices.add(i)
                        continue
            
            if i not in skip_indices:
                filtered.append(word)
        
        return ' '.join(filtered).strip()
    

    def extract_title(self, text: str, date_obj: Optional[datetime] = None) -> str:
        doc = self.nlp(text)
        
        tokens_to_skip = self._identify_tokens_to_skip(doc)
        infinitive_tokens = self._extract_infinitive_phrases(doc)
        
        title = self._build_title_from_tokens(doc, tokens_to_skip, infinitive_tokens)
        if title:
            return title
        
        title = self._build_title_fallback(doc, tokens_to_skip)
        if title:
            return title
        
        title = self._filter_words_fallback(text)
        if title:
            return title
        
        return text.strip()
    

    def parse(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "title": "",
                "datetime": None,
                "end_time": None,
                "type": "event"
            }
        
        time_range = extract_time_range(text)
        normalized = normalize_text(text)
        intent_type = self.detect_intent(normalized)
        date_obj = self.extract_datetime(normalized)
        
        if time_range:
            start_time, end_time = time_range
            if date_obj:
                start_datetime = merge_datetime_time(date_obj, start_time)
                end_datetime = merge_datetime_time(date_obj, end_time)
            else:
                start_datetime = merge_datetime_time(datetime.now(), start_time)
                end_datetime = merge_datetime_time(datetime.now(), end_time)
            
            title = self.extract_title(normalized, start_datetime)
            
            return {
                "title": title,
                "datetime": start_datetime.isoformat(),
                "end_time": end_datetime.isoformat(),
                "type": intent_type
            }
        
        time_tuple = self.extract_time(text, date_obj)
        
        if date_obj and time_tuple:
            date_obj = merge_datetime_time(date_obj, time_tuple)
        elif time_tuple and not date_obj:
            date_obj = merge_datetime_time(datetime.now(), time_tuple)
        
        title = self.extract_title(normalized, date_obj)
        
        datetime_str = date_obj.isoformat() if date_obj else None
        
        return {
            "title": title,
            "datetime": datetime_str,
            "end_time": None,
            "type": intent_type
        }
