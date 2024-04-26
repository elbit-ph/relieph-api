# coding: utf-8
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from .database import Base, Session, engine

Base = declarative_base()
metadata = Base.metadata

class Address(Base):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True, server_default=text("nextval('addresses_id_seq'::regclass)"))
    owner_id = Column(Integer, nullable=False)
    owner_type = Column(String(50), nullable=False)
    region = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    brgy = Column(String(255), nullable=False)
    street = Column(Text, nullable=False)
    zipcode = Column(Integer, nullable=False)
    coordinates = Column(String(255))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class Headline(Base):
    __tablename__ = 'headlines'

    id = Column(Integer, primary_key=True, server_default=text("nextval('headlines_id_seq'::regclass)"))
    title = Column(String(255), nullable=False)
    link = Column(Text, nullable=False)
    disaster_type = Column(String(50), nullable=False)
    posted_datetime = Column(DateTime(True), nullable=False)
    created_at = Column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))
    article = Column(Text, nullable=False)


class GenerateRelief(Base):
    __tablename__ = 'generated_relief'

    id = Column(Integer, primary_key=True, server_default=text("nextval('generated_relief_id_seq'::regclass)"))
    headline_id = Column(ForeignKey('headlines.id'), nullable=False)
    relief_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    monetary_goal = Column(Numeric, server_default=text("0.00"))
    deployment_date = Column(Date, nullable=False)
    is_used = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))

    headline = relationship('Headline')


class GeneratedInkind(Base):
    __tablename__ = 'generated_inkind'
    
    id = Column(Integer, primary_key=True, server_default=text("nextval('generated_inkind_id_seq'::regclass)"))   
    generated_relief_id = Column(ForeignKey('generated_relief.id'), nullable=False)
    item = Column(String(255), nullable=False)
    item_desc = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)

    generated_relief = relationship('GenerateRelief')
    

class InkindDonationRequirement(Base):
    __tablename__ = 'inkind_donation_requirements'

    id = Column(Integer, primary_key=True, server_default=text("nextval('inkind_donation_requirements_id_seq'::regclass)"))
    relief_id = Column(Integer, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(String(250))
    count = Column(Integer, server_default=text("0"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class ReceivedMoney(Base):
    __tablename__ = 'received_money'

    id = Column(Integer, primary_key=True, server_default=text("nextval('received_money_id_seq'::regclass)"))
    donor_id = Column(Integer, nullable=False)
    relief_id = Column(Integer, nullable=False)
    amount = Column(Numeric, nullable=False)
    platform = Column(String(75), nullable=False)
    reference_no = Column(String(255))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class ReliefBookmark(Base):
    __tablename__ = 'relief_bookmarks'

    id = Column(Integer, primary_key=True, server_default=text("nextval('relief_bookmarks_id_seq'::regclass)"))
    user_id = Column(Integer, nullable=False)
    relief_id = Column(Integer, nullable=False)
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class ReliefComment(Base):
    __tablename__ = 'relief_comments'

    id = Column(Integer, primary_key=True, server_default=text("nextval('relief_comments_id_seq'::regclass)"))
    user_id = Column(Integer, nullable=False)
    relief_id = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class ReliefEffort(Base):
    __tablename__ = 'relief_efforts'

    id = Column(Integer, primary_key=True, server_default=text("nextval('relief_efforts_id_seq'::regclass)"))
    owner_id = Column(Integer, nullable=False)
    owner_type = Column(String(50), nullable=False)
    disaster_type = Column(String(80), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    monetary_goal = Column(Numeric, server_default=text("0.00"))
    phase = Column(String(50), nullable=False, server_default=text("'Preparing'::character varying"))
    is_active = Column(Boolean, server_default=text("false"))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))
    account_number = Column(String(100))
    money_platform = Column(String(200))
    deployment_date = Column(Date)


class ReliefPaymentKey(Base):
    __tablename__ = 'relief_payment_keys'

    id = Column(Integer, primary_key=True, server_default=text("nextval('relief_payment_keys_id_seq'::regclass)"))
    owner_id = Column(Integer, nullable=False)
    owner_type = Column(String(30), nullable=False)
    p_key = Column(Text, nullable=False)
    created_at = Column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))
    s_key = Column(Text, nullable=False)


class ReliefUpdate(Base):
    __tablename__ = 'relief_updates'

    id = Column(Integer, primary_key=True, server_default=text("nextval('relief_updates_id_seq'::regclass)"))
    relief_id = Column(Integer, nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    media_dir = Column(String(255))
    type = Column(String(50), nullable=False, server_default=text("'ANNOUNCEMENT'::character varying"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class UsedMoney(Base):
    __tablename__ = 'used_money'

    id = Column(Integer, primary_key=True, server_default=text("nextval('used_money_id_seq'::regclass)"))
    relief_id = Column(Integer, nullable=False)
    amount = Column(Numeric, nullable=False)
    description = Column(String(255))
    purchase_type = Column(String(100), nullable=False)
    reference_no = Column(String(255), server_default=text("NULL::character varying"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class UserUpgradeRequest(Base):
    __tablename__ = 'user_upgrade_requests'

    id = Column(Integer, primary_key=True, server_default=text("nextval('user_upgrade_requests_id_seq'::regclass)"))
    user_id = Column(Integer, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    sex = Column(String(50), nullable=False)
    birthday = Column(Date, nullable=False)
    accountno = Column(String(60), nullable=False)
    id_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, server_default=text("'PENDING'::character varying"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, server_default=text("nextval('users_id_seq'::regclass)"))
    first_name = Column(String(255), server_default=text("NULL::character varying"))
    last_name = Column(String(255), server_default=text("NULL::character varying"))
    username = Column(String(255), nullable=False)
    password = Column(String(255), server_default=text("NULL::character varying"))
    email = Column(String(255), server_default=text("NULL::character varying"))
    mobile = Column(String(255), server_default=text("NULL::character varying"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    level = Column(SmallInteger, nullable=False, server_default=text("0"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))
    sponsor_id = Column(Integer)
    is_verified = Column(Boolean, nullable=False, server_default=text("false"))


class VerificationCode(Base):
    __tablename__ = 'verification_codes'

    id = Column(Integer, primary_key=True, server_default=text("nextval('verification_codes_id_seq'::regclass)"))
    user_id = Column(Integer, nullable=False)
    code = Column(String(50), nullable=False)
    reason = Column(String(50), nullable=False)
    created_at = Column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    expired_at = Column(DateTime(True), nullable=False)


class VolunteerRequirement(Base):
    __tablename__ = 'volunteer_requirements'

    id = Column(Integer, primary_key=True, server_default=text("nextval('volunteer_requirements_id_seq'::regclass)"))
    relief_id = Column(Integer, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(String(250))
    count = Column(Integer, server_default=text("0"))
    duration_days = Column(Integer, server_default=text("1"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))


class InkindDonation(Base):
    __tablename__ = 'inkind_donations'

    id = Column(Integer, primary_key=True, server_default=text("nextval('inkind_donations_id_seq'::regclass)"))
    relief_id = Column(Integer, nullable=False)
    inkind_requirement_id = Column(ForeignKey('inkind_donation_requirements.id'), nullable=False)
    donor_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, server_default=text("1"))
    expiry = Column(Date, nullable=False)
    status = Column(String(50))
    platform = Column(String(50))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))

    inkind_requirement = relationship('InkindDonationRequirement')


class Organization(Base):
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True, server_default=text("nextval('organizations_id_seq'::regclass)"))
    owner_id = Column(ForeignKey('users.id'), nullable=False)
    sponsor_id = Column(Integer)
    tier = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    is_active = Column(Boolean, server_default=text("false"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))

    owner = relationship('User')


class Report(Base):
    __tablename__ = 'report'

    id = Column(Integer, primary_key=True, server_default=text("nextval('report_id_seq'::regclass)"))
    user_id = Column(ForeignKey('users.id'), nullable=False)
    reason = Column(Text, nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, server_default=text("'pending'::character varying"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))

    user = relationship('User')


class Volunteer(Base):
    __tablename__ = 'volunteers'

    id = Column(Integer, primary_key=True, server_default=text("nextval('volunteers_id_seq'::regclass)"))
    relief_id = Column(Integer, nullable=False)
    volunteer_requirement_id = Column(ForeignKey('volunteer_requirements.id'), nullable=False)
    volunteer_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, server_default=text("'FOR APPROVAL'::character varying"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))

    volunteer_requirement = relationship('VolunteerRequirement')


class SponsorshipRequest(Base):
    __tablename__ = 'sponsorship_requests'

    id = Column(Integer, primary_key=True, server_default=text("nextval('sponsorship_requests_id_seq'::regclass)"))
    owner_id = Column(ForeignKey('organizations.id'), nullable=False)
    foundation_id = Column(ForeignKey('organizations.id'), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(100))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(True))
    owner_type = Column(String(30), nullable=False)

    foundation = relationship('Organization', primaryjoin='SponsorshipRequest.foundation_id == Organization.id')
    owner = relationship('Organization', primaryjoin='SponsorshipRequest.owner_id == Organization.id')
    
Base.metadata.create_all(engine)