from sqlalchemy import and_
from datetime import datetime

from services.db.database import Session
from services.db.models import Report, ReliefComment, Organization, ReliefEffort, User

class ReportsHandler():
    def __init__(self):
        self.valid_types = ['COMMENTS', 'RELIEF', 'ORGANIZATION']
        self.valid_statuses = ['PENDING', 'RESOLVED', 'DELETED', 'ALL']
        self.db = Session()
    
    def create_report(self, target_type:str, target_id:int, reason:str, user_id:int):

        # check if target type is valid
        if target_type.upper() not in self.valid_types:
            return ('InvalidType', False)
        
        # check if target exists
        target = self.retrieve_target(target_type, target_id)
        if target == False:
            return target

        # create new report
        report = Report()
        report.user_id = user_id
        report.reason = reason
        report.target_id = target_id
        report.target_type = target_type
        report.status = 'PENDING'

        self.db.add(report)

        self.db.commit()

        return ('Successful', True)
    
    def retrieve_reports(self, target_type:str, status:str, p:int, c:int):

        # check if `status` is valid
        if status.upper() not in self.valid_statuses:
            return ('InvalidStatus', False)

        # checks if type is valid
        if target_type.upper() not in self.valid_types:
            return ('InvalidType', False)

        # retrieves data
        reports = self.db.query(Report).filter(and_(Report.is_deleted == False, Report.status == status, Report.target_type == type)).limit(c).offset((p-1)*c).all()

        return (reports, True)

    def retrieve_target(self, target_type, target_id):
        target = None

        match target_type:
            case 'comment':
                target = self.db.query(ReliefComment).filter(and_(ReliefComment.id == target_id, ReliefComment.is_deleted == False)).first()
            case 'relief':
                target = self.db.query(ReliefEffort).filter(and_(ReliefEffort.id == target_id, ReliefEffort.is_deleted == False)).first()
            case 'organization':
                target = self.db.query(Organization).filter(and_(Organization.id == target_id, Organization.is_deleted == False)).first()
        
        if target is None:
            return ('TargetNotFound', False)
        
        return ('target', True)

    def takedown_target(self, report_id:int):
        
        report:Report = self.db.query(Report).filter(and_(Report.id == report_id, Report.status == 'PENDING')).first()

        # check if report exists
        if report is None:
            return {'ReportNotFound', False}
        
        # check if report was already taken down
        if report.status == 'REMOVED':
            return {'ReportAlreadyRemoved', False}

        # get target
        target = self.retrieve_target(report.target_type, report.target_id)
        
        # delete target and update other fields
        report.status = 'REMOVED'
        report.updated_at = datetime.now()
        self.db.delete(target)
        
        # save changes
        self.db.commit()

        return ('Success', True)
    
    def resolve_target(self, report_id:int):
        # essentially marks report as resolved

        report:Report = self.db.query(Report).filter(and_(Report.id == report_id, Report.status == 'PENDING')).first()

        # check if report exists
        if report is None:
            return {'ReportNotFound', False}
        
        # check if report was already taken down
        if report.status == 'REMOVED':
            return {'ReportAlreadyRemoved', False}
        
        report.status = 'resolved'
        report.updated_at = datetime.now()

        return ('Success', True)