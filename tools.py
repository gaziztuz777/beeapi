#!/usr/bin/python3.4 python
from models import get_session, get_class, show_all_values, Properties
from client import Rest, Soap
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_
from datetime import datetime
import warnings
from openpyxl import Workbook
import logging
from errors import DatabaseError



def ex_write(values, names=['col1', 'col2', 'col3'],
             path='result.xlsx', wsname='Sheet1'):
    wb = Workbook(write_only=True)
    ws = wb.create_sheet()
    ws.title = wsname
    ws.append(names)
    for row in range(len(values)):
        ws.append(values[row])

    wb.save(path)


def get_mass_serv():
    session = get_session('ekomobile')

    rapi = Rest()
    services = get_class('service_fx')
    agree = get_class('operator_agree')
    ctn = get_class('ctn')
    btp = get_class('operator_tarif')
    banlist = session.query(agree.i_id).filter(agree.moboperator == 1, agree.payment_type == 0,
                                               agree.discontinued == 0).all()
    banlist = [el[0] for el in banlist]
    ctnlist = session.query(ctn.msisdn, ctn.operator_tarif).filter(
        ctn.operator_agree.in_(banlist), ctn.status == 1).group_by(ctn.operator_tarif).all()
    result = []

    for el in ctnlist:

        rapi.change_owner(ctn=int(el[0]))
        rez = rapi.get_available_services()['availableServices']
        if len(rez) == 0:
            print(rapi.ctn)
        for r in rez:
            tarif = session.query(btp.name).filter(btp.i_id == int(el[1])).one()[0]
            try:
                serv = session.query(services.i_id).filter(services.bee_sync == r['name']).one()[0]
            except NoResultFound:
                serv = 'Нет в билле!'
            result.append([rapi.ctn, el[1], tarif, serv, r['name'], r['entityName'], r['rcRate']])
        print('{} из {}'.format(ctnlist.index(el) + 1, len(ctnlist)))

    names = ['Номер', 'Тариф', 'Техкод услуги', 'Название услуги', 'АП услуги']

    session.close()
    try:
        ex_write(names, result, path='C:/Users/ГостЪ/Desktop/services.xlsx')
    except ValueError:
        return result
    else:
        return


def check_bills():
    """проверка наличия услуг в биллинге"""
    ser = get_class('hstr_service_fx')
    service_fx = get_class('service_fx')
    session = get_session('ekomobile')

    file = open('C:/Users/админ/Desktop/1.txt').readlines()
    rez_f = []
    for el in file:
        phone, off, on = el.split(';')
        rez_f.append({'phone': phone.rstrip(), 'on': on.rstrip(), 'off': off.rstrip()})

    on = [[el['phone'], el['on']] for el in rez_f if el['on'] != '']
    off = [[el['phone'], el['off']] for el in rez_f if el['off'] != '']

    for el in on:
        phone, service = el
        try:
            sid = session.query(service_fx.i_id).filter(service_fx.bee_sync == service.rstrip()).one()[0]
        except NoResultFound:
            print(el, 'неверные параметры, должна быть подключена')
            continue

        hstr = session.query(ser).filter(ser.object_id == phone.rstrip(),
                                         ser.service_id == sid,
                                         ser.activated < datetime.now(),
                                         or_(not ser.deactivated,
                                             ser.deactivated > datetime.now())).all()
        if len(hstr) == 0:
            print(el, ' не подключена, должна быть подключена')

    for el in off:
        phone, service = el
        try:
            sid = session.query(service_fx.i_id).filter(service_fx.bee_sync == service.rstrip()).one()[0]
        except NoResultFound:
            print(el, 'неверные параметры, должна быть отключена')
            continue
        hstr = session.query(ser).filter(ser.object_id == phone.rstrip(),
                                         ser.service_id == sid,
                                         ser.deactivated < datetime.now(),
                                         or_(not ser.deactivated,
                                             ser.deactivated > datetime.now())).all()
        if len(hstr) != 0:
            print(el, ' не отклчена, должна быть отключена')
    session.close()


def get_off_services():
    session = get_session('ekomobile')
    services = get_class('service_fx')
    hstr_services = get_class('hstr_service_fx')
    result = []
    sers = session.query(hstr_services.object_id, hstr_services.service_id).\
        filter(or_(not hstr_services.deactivated,
                   hstr_services.deactivated > datetime.now())).\
        group_by(hstr_services.service_id).all()
    print('Get services list')

    for rec in sers:

        rapi = Rest(ctn=int(rec[0]))
        ser_name = session.query(services.bee_sync).filter(services.i_id == int(rec[1]), services).one()[0]
        api_sers = rapi.get_services_list()['services']
        for ser in api_sers:
            if ser['name'] == ser_name:
                result.append([ser_name, ser['removeInd']])
        if result[-1][0] != ser_name:
            warnings.warn('Kosyak, phone={}, service={}'.format(rapi.ctn, ser_name))
        print('Made {} of {}'.format(sers.index(rec)+1, len(sers)))
    session.close()
    try:
        ex_write(['code', 'y/n'], result, "C:/Users/админ/Desktop/remove_services.xlsx")
    except Exception:
        return result


def check_subscription(nums, show=False, for_return=False):

    rapi = Rest()

    rez = []
    for phone in nums:
        try:
            rapi.change_owner(ctn=str(phone).strip())
        except NoResultFound:
            continue
        subscrs = rapi.get_subscriptions()['subscriptions']
        if len(subscrs) > 0:
            rez.append(rapi.ctn)
            if show:
                for el in subscrs:
                    print(el[''])
        print('Check {} of {}'.format(nums.index(phone)+1, len(nums)))
    print('Now count of numbers with active subscriptions = {}'.format(len(rez)))

    if len(rez) > 0:
        print('Numbers with subscriptions:')
        for el in rez:
            print(str(el))


def remove_subscription(nums='C:/Users/админ/Desktop/1.txt', begin=0, show=False):
    rapi = Rest()
    count = 0

    if not isinstance(nums, list):
        nums = open(nums).readlines()
    for phone in nums[begin:]:
            rapi.change_owner(ctn=str(phone).strip())
            try:
                subscrs = rapi.get_subscriptions()['subscriptions']
            except KeyError:
                print(rapi.get_subscriptions())
            count += len(subscrs)
            for el in subscrs:
                rapi.remove_subscription(
                    subscription_id=el['id'], subscription_type=el['type'])
            if len(subscrs) > 0:
                print('Made {} request(-s) for {}th of {} numbers'.format(
                    len(subscrs),
                    nums.index(phone)+1,
                    len(nums)
                ))
            else:
                print("Didn't found subscriptions on {}.\n{}th of {} numbers".format(
                    rapi.ctn,
                    nums.index(phone)+1,
                    len(nums)
                ))
                nums.remove(phone)
    print('Totally made {} requests for remove subscriptions'.format(count))
    if count != 0:
        check_subscription(nums, show)

# TODO refactoring and optimization
def update_objects(classname, key, u_id, path='C:/Users/админ/Desktop/1.txt', insert=False, test=False):
    """required classname and key"""

    session = get_session('ekomobile')
    c_class = get_class(classname)
    if input('First line - system names, second and other - values (Y/n)? ') not in ["y", "Y", ""]:
        return
    if test:
        raise AttributeError('Unavailable')
    with open(path) as file:
        names = [el.strip() for el in file.readline().split('\t')]
        ch = False
        for name in names:
            if name not in c_class.__attr_list__:
                warnings.warn('{} is not attribute of {} class'.format(name, classname))
                ch = True
        if ch:
            return
        values = file.readlines()
        for val in values:
            # if it possible - making digits, else stripping
            val_u = [int(el) if el.strip().isdigit() else el.strip() for el in val.split('\t')]
            items = dict(zip(names, val_u))
            try:
                try:
                    obj_list = session.query(c_class).filter(getattr(c_class, key) == items[key]).all()
                except Exception:
                    print(items.keys())
                    raise Exception
            except NoResultFound:
                if not insert:
                    logging.log(logging.DEBUG, 'Classname {} with id = {} not found!'.format(
                        classname, items[key]
                    ))
                else:
                    insert_data(classname, data=[items])
                    print("Inserted record with key {}".format(items[key]))
            else:
                for obj in obj_list:
                    for col_name in items:
                        # if value not null...
                        if items[col_name]:
                            setattr(obj, col_name, items[col_name])
                    obj.date_ch = datetime.now()
                    obj.user_id = u_id
            session.commit()
            ind = values.index(val)+1
            if ind % 100 == 0 and ind != 0:
                print('Ready {} of {}'.format(values.index(val)+1, len(values)))
        print('That\'s all')
        if test:
            def print_names(names):
                for name in names:
                    print(name, end="\t")
                print('\n-------------------------------------------------------------------------------------------')
            rows = session.query(c_class).all()
            print_names(names)
            for row in rows:
                if rows.index(row) % 20 == 0:
                    print_names(names)

                for name in names:
                    print(str(getattr(row, name)), end = '\t')
                print()
    session.close()


# TODO refactoring and optimization
def insert_data(classname, u_id, path=None, ctn=False, data=None, test=False):

    session = get_session('ekomobile')
    c_class = get_class(classname)
    if test:
        raise AttributeError('Unavailable')
    if not path and not data:
        raise AttributeError("Required file or data")
    if data and not isinstance(data, list):
        data = [data]

    elif not data:
        if input('First line - system names, second and other - values (Y/n)? ') not in ["y,Y", ""]:
            return
        file = open(path)
        names = [name.strip() for name in file.readline().split('\t')]
        ch = False
        for name in names:
            if name not in c_class.__attr_list__:
                print('{} is not attribute of {} class'.format(name, classname))
                ch = True
        if ch:
            return
        data = [line.rstrip().split('\t') for line in file.readlines() if line.strip()]
        data = [dict(zip(names, val)) for val in data]
    for row in data:
        if row == '\n':
            continue
        to_insert = c_class(date_in=datetime.now(), date_ch=datetime.now(), user_id=u_id)
        for key in row:
            if row[key]:
                setattr(to_insert, key, row[key])
        session.add(to_insert)
        ind = data.index(row) + 1
        if ind % 100 == 0 and ind != 0:
            print('Inserted {} of {}'.format(ind, len(data)))
    print('Commit...')
    session.commit()
    if test:
        objects = dict()
        for name in names:
            try:
                objects[name] = get_class(name)
            except DatabaseError:
                pass

        def print_names(names):
            for name in names:
                print(name, end="\t")
            print('\n-------------------------------------------------------------------------------------------')

        rows = session.query(c_class).all()
        print_names(names)
        for row in rows:
            if rows.index(row) % 20 == 0:
                print_names(names)
            for name in names:
                print(str(getattr(row, name)), end = '\t')
            print()
    session.close()
    print('that\'s all')

def get_detail(beg=0):
    ctn = get_class('ctn')
    ses = get_session('ekomobile')
    ctn_list = ses.query(ctn).filter(ctn.operator_agree.in_([404,405])).all()
    result_detail = []
    null_phones = []
    for phone in ctn_list[beg:]:
        try:
            api = Soap(ctn=phone.msisdn)
            dt = api.get_current_detail()
        except Exception:
            print("Последний - {}, {}".format(phone.msisdn, ctn_list.index(phone)))
            print(null_phones)
            return

        if len(dt) == 0:
            null_phones.append(phone.msisdn)
        result_detail.extend(dt)
        print("Ready {} of {}".format(ctn_list.index(phone)+1, len(ctn_list)))
    print(null_phones)
    ex_write(values=result_detail,
             names=["Дата", "Исходящий", "Входящий", "Тип соединения", "Описание звонка", "Трафик", "Стоимость", "Длительность"],
             path="/home/spicin/dt.xlsx")

def get_as_info():
    sapi = Soap(login="A390906555", password="B39090600")
    sapi.ban = sapi.get_ban_info()[0].ban
    print('get ban info')
    ctn_list = sapi.get_ctn_info(level='ban')
    print('get ctn list')
    write_list = []
    for phone in ctn_list:
        write_list.append([
            str(phone.ctn[1:]),
            str(phone.status),
            str(phone.statusDate),
            str(phone.pricePlan)]
        )
        print('get {} of {}'.format(ctn_list.index(phone)+1, len(ctn_list)))
    ex_write(values=write_list, names=['msisdn', 'status', 'status_date', 'price_plan', 'price_plan_time'], path='/home/spicin/as.xlsx')



if __name__ == "__main__":
    login = input('Логин? ')
    password = input('Пароль? ')
    session = get_session('ekomobile')
    user = get_class('user')
    try:
        u_id = session.query(user.i_id).filter_by(login=login, password=password).one()
    except NoResultFound:
        input("Неверные данные для входа")
        exit()
    ch = int(input('Обновляем(1) или заливаем новое(2)? '))
    if ch not in [1, 2]:
        input('Нет такого варианта')
        exit()
    file = input("Введите имя файла (с .txt на конце) ")
    classname = input('Имя класса? ')
    if ch == 1:
        key = input('К чему привязываемся? ')
        update_objects(classname, key, u_id, file)
    elif ch == 2:
        insert_data(classname, u_id, file)

