from jmcomic import *
from jmcomic.cl import JmcomicUI

# 下方填入你要下载的本子的id，一行一个，每行的首尾可以有空白字符
jm_albums = str_to_list('''
625305
590827
79575
1215448
95144
20947
14485
1213347
1202118
1198896
1124922
605769
225813
1230550
602513
433789
484921
432466
317935
1023960
501847
1199392
188197
146878
93249
1208643
1199846
1046521
526117
643779
408307
231103
1209081
1209971
368827
368774
1142773
513653
347468
217691
1229605
503144
415522
407853
1061343
1033842
600576
528853
427454
1203781
1050774
614666
465027
1227557
564037
1045577
1222709
1212874
1082839
483826
567254
400506
241601
258115
460128
234124
119744
1171683
92134
302366
1063818
495851
542765
1204715
649156
1069508
1223365
1222347
1216628
1225347
1218497
477572
526216
151997
637409
1178334
1179136
1026681
1113207
1060422
242785
1128067
627171
485319
211342
433291
607337
644156
541165
1052122
1099825
1124870
595470
1077824
575798
559792
1090172
612803
205181
152604
374061
273098
188627
530503
497723
646452
1071993
1071648
1069332
1063432
597920
604166
410553
305015
529553
400169
144132
380772
472930
596436
192245
395792
540852
614639
547212
415296
646834
646886
340547
309112
508570
640545
627869
633484
593504
619549
419340
640555
618588
495053
564020
637718
501472
554317
643796
224057
420082
626611
594046
596486
517760
623390
635946
373097
582577
553058
617121
604196
314730
564058
406543
523642
618802
34155
306279
385739
365173
498944
539437
561716
562991
87661
480853
302046
530949
620234
469220
617419
619547
616549
453961
579282
354977
398986
518074
463262
481317
581566
541606
575151
615097
401576
397500
548983
619523
402908
434607
617387
529782
610591
614171
614137
608759
504322
209251
559769
577562
553414
568565
345004
608822
481732
428172
179942
511412
404477
589714
597350
600339
600338
526184
579318
598334
599077
368001
188640
229730
389982
527685
514232
523562
251853
387590
337898
577946
83580
35961
319843
319719
248321
99108
102442
96056
496511
524864
494650
513534
147742
388768
413209
317917
357008
313784
372789
415770
114058
534022
525770
534640
534573
206537


''')

# 单独下载章节
jm_photos = '''



'''


def env(name, default, trim=('[]', '""', "''")):
    import os
    value = os.getenv(name, None)
    if value is None or value == '':
        return default

    for pair in trim:
        if value.startswith(pair[0]) and value.endswith(pair[1]):
            value = value[1:-1]

    return value


def get_id_set(env_name, given):
    aid_set = set()
    for text in [
        given,
        (env(env_name, '')).replace('-', '\n'),
    ]:
        aid_set.update(str_to_set(text))

    return aid_set


def main():
    album_id_set = get_id_set('JM_ALBUM_IDS', jm_albums)
    photo_id_set = get_id_set('JM_PHOTO_IDS', jm_photos)

    helper = JmcomicUI()
    helper.album_id_list = list(album_id_set)
    helper.photo_id_list = list(photo_id_set)

    option = get_option()
    helper.run(option)
    option.call_all_plugin('after_download')


def get_option():
    # 读取 option 配置文件
    option = create_option(os.path.abspath(os.path.join(__file__, '../../assets/option/option_workflow_download.yml')))

    # 支持工作流覆盖配置文件的配置
    cover_option_config(option)

    # 把请求错误的html下载到文件，方便GitHub Actions下载查看日志
    log_before_raise()

    return option


def cover_option_config(option: JmOption):
    dir_rule = env('DIR_RULE', None)
    if dir_rule is not None:
        the_old = option.dir_rule
        the_new = DirRule(dir_rule, base_dir=the_old.base_dir)
        option.dir_rule = the_new

    impl = env('CLIENT_IMPL', None)
    if impl is not None:
        option.client.impl = impl

    suffix = env('IMAGE_SUFFIX', None)
    if suffix is not None:
        option.download.image.suffix = fix_suffix(suffix)

    pdf_option = env('PDF_OPTION', None)
    if pdf_option and pdf_option != '否':
        call_when = 'after_album' if pdf_option == '是 | 本子维度合并pdf' else 'after_photo'
        plugin = [{
            'plugin': Img2pdfPlugin.plugin_key,
            'kwargs': {
                'pdf_dir': option.dir_rule.base_dir + '/pdf/',
                'filename_rule': call_when[6].upper() + 'id',
                'delete_original_file': True,
            }
        }]
        option.plugins[call_when] = plugin


def log_before_raise():
    jm_download_dir = env('JM_DOWNLOAD_DIR', workspace())
    mkdir_if_not_exists(jm_download_dir)

    def decide_filepath(e):
        resp = e.context.get(ExceptionTool.CONTEXT_KEY_RESP, None)

        if resp is None:
            suffix = str(time_stamp())
        else:
            suffix = resp.url

        name = '-'.join(
            fix_windir_name(it)
            for it in [
                e.description,
                current_thread().name,
                suffix
            ]
        )

        path = f'{jm_download_dir}/【出错了】{name}.log'
        return path

    def exception_listener(e: JmcomicException):
        """
        异常监听器，实现了在 GitHub Actions 下，把请求错误的信息下载到文件，方便调试和通知使用者
        """
        # 决定要写入的文件路径
        path = decide_filepath(e)

        # 准备内容
        content = [
            str(type(e)),
            e.msg,
        ]
        for k, v in e.context.items():
            content.append(f'{k}: {v}')

        # resp.text
        resp = e.context.get(ExceptionTool.CONTEXT_KEY_RESP, None)
        if resp:
            content.append(f'响应文本: {resp.text}')

        # 写文件
        write_text(path, '\n'.join(content))

    JmModuleConfig.register_exception_listener(JmcomicException, exception_listener)


if __name__ == '__main__':
    main()
