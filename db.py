from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Boolean, Integer, Text, DateTime, PickleType
from sqlalchemy import CheckConstraint
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased, relationship, Session
import datetime
import pathlib
import sys
import random
import math

Base = declarative_base()

class Program(Base):
    __tablename__ = 'program'
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(Text, default='', nullable=False, index=True)
    dir = Column(Text, default='', nullable=False, index=True)
    
    linked_to_id = Column(Integer, ForeignKey('program.id'), default=None)
    
    days = Column(PickleType, nullable=False)
    mode = Column(Text,
        CheckConstraint("mode in ('normal', 'repeat', 'random')"),
        default='normal', nullable=False)
    n = Column(Integer, default=1, nullable=False)
    opening = Column(Text, default='', nullable=False)
    ending = Column(Text, default='', nullable=False)
    
    stopped = Column(Boolean, default=False, nullable=False)
    
    last_file = Column(Text, default='', nullable=False)
    last_files = Column(PickleType, default=[], nullable=False)
    next_datetime = Column(DateTime)
    
    linked_to = relationship('Program', back_populates='linked', remote_side=[id])
    linked = relationship('Program', back_populates='linked_to', cascade='delete')
    
    @property
    def time(self):
        return self.days.time
    
    def do_next(self):
        files = sorted([c for c in pathlib.Path(self.dir).glob('*')
            if not c.name.startswith('__') and c.is_file() and
            c.name not in [self.opening, self.ending]])
        if self.mode == 'normal':
            next_files = [c for c in files if c.name > self.last_file]
            if self.n >= 1:
                return next_files[0:self.n]
            else:
                return next_files
        elif self.mode == 'random':
            return files
        else:
            #repeat
            next_files = [c for c in files if c.name > self.last_file]
            if next_files:
                next_files_idx = files.index(next_files[0])
            else:
                next_files_idx = len(files)
            
            next_files.extend(files[0:next_files_idx])
            if self.n >= 1:
                if next_files:
                    next_files *= math.ceil(self.n/len(next_files))
                return next_files[0:self.n]
            else:
                return next_files
    
    def next(self, set_last_files=False):
        if self.linked_to is not None:
            if self.mode == 'repeat':
                return self.linked_to.last_files
            elif self.linked_to.linked_to is None:
                return self.linked_to.next(set_last_files)
            else:
                print(
                    'detected linked program to a linked program. this is invalid. this program will always be ignored.', file=sys.stderr)
        else:
            if self.mode == 'random':
                all_files = self.do_next()
                n = self.n
                next_files = []
                while n > 0:
                    next_files.extend(
                        random.sample(all_files, min(n, len(all_files))))
                    n -= len(next_files)
            else:
                next_files = self.do_next()
            
            if set_last_files:
                self.last_files = next_files
                if next_files and self.mode != 'random':
                    self.last_file = next_files[-1].name
            elif self.mode == 'random':
                self.last_file = ''
                    
            return next_files
    
    def advance(self, ref_time=None):
        if ref_time is None:
            ref_time = self.next_datetime
        
        next_time = self.days.next_time(ref_time)
        self.next_datetime = next_time
    
    def __repr__(self):
        if self.linked_to is not None:
            return '<Program linked to {}({})>'.format(self.linked_to.name,
                self.linked_to.dir)
        else:
            return '<Program {}({})>'.format(self.name, self.dir)

def get_object(obj, type_, session=None):
    if obj is None:
        return obj
    elif type(obj) is not type_:
        obj = session.query(type_).get(obj)
    return obj

def edit_program_no_commit(program, name, dir, days, mode='normal', n=1,
        opening='', ending='', linked_to=None, stopped=False, last_file=None,
        session=None):
    if session is None:
        session = Session.object_session(program)
    
    if not program:
        program = Program()
        session.add(program)
    else:
        program = get_object(program, Program, session)
    
    linked_to = get_object(linked_to, Program, session)
    
    next_datetime = days.next_time()
    
    program.name = name
    program.dir = str(pathlib.Path(dir).resolve())
    program.linked_to = linked_to
    program.days = days
    program.mode = mode
    program.n = n
    program.opening = opening
    program.ending = ending
    program.next_datetime = next_datetime
    program.stopped = stopped
    
    if last_file is not None:
        program.last_file = last_file
    
    return program

def edit_program(program, name, dir, days, mode='normal', n=1,
        opening='', ending='', linked_to=None, stopped=False, last_file=None,
        session=None):
    if session is None:
        session = Session.object_session(program)
    out = edit_program_no_commit(program, name, dir, days, mode, n, opening,
        ending, linked_to, stopped, last_file, session)
    commit_session(session)
    return out

def delete_program_no_commit(program, session=None):
    if session is None:
        session = Session.object_session(program)
    
    delete_obj(program, Program, session)

def delete_program(program, session=None):
    if session is None:
        session = Session.object_session(program)
    out = delete_program_no_commit(program, session)
    commit_session(session)
    return out

def delete_obj(obj, type_=None, session=None):
    if type_ is None:
        type_ = type(obj)
        session = Session.object_session(obj)
    
    obj = get_object(obj, type_, session)
    
    session.delete(obj)

def advance_program_no_commit(program, ref_time=None, session=None):
    if type(program) is not Program:
        program = session.query(Program).get(program)
    
    next_files = program.next(True)
    program.advance(ref_time)
    
    return next_files

def advance_program(program, ref_time=None, session=None):
    if session is None:
        session = Session.object_session(program)
    out = advance_program_no_commit(program, ref_time, session)
    commit_session(session)
    return out

def program_set_stopped(program, stopped, session=None):
    if session is None:
        session = Session.object_session(program)
    
    program = get_object(program, Program, session)
    program.stopped = stopped

def stop_program_no_commit(program, session=None):
    if type(program) is not Program:
        program = session.query(Program).get(program)
    
    program_set_stopped(session, program, True)

def stop_program(program, session=None):
    if session is None:
        session = Session.object_session(program)
    out = stop_program_no_commit(program, session=None)
    commit_session(session)
    return out

def unstop_program_no_commit(program, session=None):
    if type(program) is not Program:
        program = session.query(Program).get(program)
    
    program_set_stopped(session, program, False)

def unstop_program(program, session=None):
    if session is None:
        session = Session.object_session(program)
    out = unstop_program_no_commit(program, session=None)
    commit_session(session)
    return out

def next_check(session):
    now = datetime.datetime.now().replace(second=0, microsecond=0)
    
    parent_program = aliased(Program)
    root_cond = and_(Program.linked_to_id == None,
        Program.stopped == False, Program.next_datetime >= now)
    sub_cond = and_(Program.linked_to_id != None,
        parent_program.stopped == False, Program.next_datetime >= now)
    
    next_check = session.query(Program).filter(
            or_(root_cond, sub_cond)
        ).outerjoin(
            parent_program, parent_program.id == Program.linked_to_id
        ).order_by(
            Program.next_datetime,
            Program.name
        ).first()
    
    return next_check

def update_programs_time(session, ref_time=None):
    if ref_time is None:
        ref_time = datetime.datetime.now()
    
    q = session.query(Program).filter(Program.next_datetime <= ref_time)
    for c in q:
        print('advancing', c)
        c.advance(ref_time)
    
    commit_session(session)

def commit_session(session):
    try:
        session.commit()
    except:
        session.rollback()
        raise
